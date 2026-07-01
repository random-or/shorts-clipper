import logging
import os
import shutil
import threading
import time
import urllib.parse
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import requests

from shorts_clipper.core.settings import Settings

from ..base import Publisher
from ..models import ClipMetadata, PublishResult

log = logging.getLogger(__name__)


class InstagramGraphPublisher(Publisher):
    """Handles publishing vertical clips to Instagram Reels using the official Meta Graph API."""

    def __init__(self):
        self.settings = Settings.from_env()

    @property
    def platform_name(self) -> str:
        return "instagram"

    def authenticate(self) -> None:
        """Verify Graph API credentials exist."""
        if not self.settings.ig_access_token or not self.settings.ig_account_id:
            raise RuntimeError("IG_ACCESS_TOKEN or IG_ACCOUNT_ID not found in settings.")
        log.info("Instagram Graph API credentials verified.")

    def _upload_temp_video(self, video_path: Path) -> str:
        """Uploads the video to a temporary public host for Meta to download."""
        log.info("Uploading video to temporary host...")

        # Define multiple fallback upload strategies
        def try_catbox() -> str:
            url = "https://catbox.moe/user/api.php"
            with open(video_path, "rb") as f:
                res = requests.post(
                    url, data={"reqtype": "fileupload"}, files={"fileToUpload": f}, timeout=600
                )
            if res.status_code != 200:
                raise RuntimeError(f"Catbox failed: {res.status_code}")
            return res.text.strip()

        def try_tmpfiles() -> str:
            url = "https://tmpfiles.org/api/v1/upload"
            with open(video_path, "rb") as f:
                res = requests.post(url, files={"file": f}, timeout=600)
            if res.status_code != 200:
                raise RuntimeError(f"Tmpfiles failed: {res.status_code}")
            data = res.json()
            # Convert https://tmpfiles.org/wiwl0qpA1I9R/test.mp4 to https://tmpfiles.org/dl/wiwl0qpA1I9R/test.mp4
            return data["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")

        def try_uguu() -> str:
            url = "https://uguu.se/upload.php"
            with open(video_path, "rb") as f:
                files = {"files[]": (video_path.name, f, "video/mp4")}
                res = requests.post(url, files=files, timeout=600)
            if res.status_code != 200:
                raise RuntimeError(f"Uguu failed: {res.status_code}")
            data = res.json()
            if not data.get("success"):
                raise RuntimeError(f"Uguu error: {data}")
            return data["files"][0]["url"]

        hosts = [("catbox.moe", try_catbox), ("tmpfiles.org", try_tmpfiles), ("uguu.se", try_uguu)]

        for name, upload_func in hosts:
            try:
                log.info(f"Trying host: {name}")
                public_url = upload_func()
                log.info(f"Successfully uploaded to {name}: {public_url}")
                return public_url
            except Exception as e:
                log.warning(f"Failed to upload to {name}: {e}")

        raise RuntimeError("All temporary file hosts failed to upload the video.")

    def _get_video_url(self, video_path: Path) -> str:
        """Determines the public URL of the video for Meta Graph API."""
        if self.settings.use_temp_hosts:
            log.warning(
                "Using deprecated temporary hosts for Instagram video upload. Set PUBLIC_URL instead."
            )
            return self._upload_temp_video(video_path)

        if not self.settings.public_url:
            raise RuntimeError(
                "PUBLIC_URL must be set in settings/env to publish to Instagram natively. Alternatively, set SHORTS_USE_TEMP_HOSTS=true to use the legacy temporary hosts."
            )

        # Create a unique hardlink to prevent collision if the original is overwritten
        hosted_dir = video_path.parent / "ig_hosted"
        hosted_dir.mkdir(exist_ok=True)
        unique_name = f"{video_path.stem}_{uuid.uuid4().hex[:8]}{video_path.suffix}"
        unique_path = hosted_dir / unique_name

        try:
            os.link(video_path, unique_path)
        except OSError:
            shutil.copy2(video_path, unique_path)

        def _cleanup_link(p: Path) -> None:
            time.sleep(3600)  # Wait 1 hour for Meta to download
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass

        threading.Thread(target=_cleanup_link, args=(unique_path,), daemon=True).start()

        base_url = self.settings.public_url.rstrip("/")
        encoded_name = urllib.parse.quote(unique_name)
        url = f"{base_url}/clips/ig_hosted/{encoded_name}"
        log.info(f"Using self-hosted video URL: {url}")
        return url

    def publish(
        self,
        video_path: Path,
        metadata: ClipMetadata,
        progress_callback: Callable[[int], None] | None = None,
    ) -> PublishResult:
        token = self.settings.ig_access_token
        ig_id = self.settings.ig_account_id

        if not token or not ig_id:
            return PublishResult(
                platform=self.platform_name,
                success=False,
                error_message="Graph API credentials missing.",
            )

        tags_str = " ".join([f"#{t}" for t in metadata.tags])
        caption = f"{metadata.title}\n\n{metadata.description}\n\n{tags_str}"

        try:
            # Step 1: Get the video URL (self-hosted or temporary)
            video_url = self._get_video_url(video_path)

            # Step 2: Create Media Container
            log.info("Initializing Reel upload via Graph API...")
            url = f"https://graph.instagram.com/v19.0/{ig_id}/media"
            payload = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": token,
            }
            res = requests.post(url, data=payload, timeout=60)
            res_data = res.json()

            if "error" in res_data:
                raise RuntimeError(f"Graph API Error: {res_data['error']['message']}")

            creation_id = res_data.get("id")
            if not creation_id:
                raise RuntimeError(f"Failed to get creation_id: {res_data}")

            # Step 3: Check Status until FINISHED
            log.info(
                f"Container created ({creation_id}). Waiting for Meta to download and process the video..."
            )
            status_url = f"https://graph.instagram.com/v19.0/{creation_id}?fields=status_code,status&access_token={token}"

            max_attempts = 60
            for attempt in range(max_attempts):
                status_res = requests.get(status_url, timeout=30).json()
                status = status_res.get("status_code")
                log.info(f"Processing status: {status} | Full response: {status_res}")
                if status == "FINISHED":
                    break
                elif status == "ERROR":
                    raise RuntimeError(
                        f"Meta failed to process the video. Full response: {status_res}"
                    )

                if progress_callback:
                    progress_callback(min(90, int(90 * (attempt / max_attempts))))
                time.sleep(5)
            else:
                raise RuntimeError("Timeout waiting for Meta to process the video.")

            # Step 4: Publish
            log.info("Processing complete. Publishing Reel to Instagram...")
            publish_url = f"https://graph.instagram.com/v19.0/{ig_id}/media_publish"
            pub_res = requests.post(
                publish_url, data={"creation_id": creation_id, "access_token": token}, timeout=30
            )
            pub_data = pub_res.json()

            if "error" in pub_data:
                raise RuntimeError(f"Publish Error: {pub_data['error']['message']}")

            published_id = pub_data.get("id")
            if progress_callback:
                progress_callback(100)

            return PublishResult(
                platform=self.platform_name,
                success=True,
                url=f"https://www.instagram.com/reel/{published_id}/" if published_id else None,
                platform_id=published_id,
                published_at=datetime.utcnow().isoformat() + "Z",
            )

        except Exception as e:
            log.error(f"Graph API Publishing failed: {e}")
            return PublishResult(platform=self.platform_name, success=False, error_message=str(e))

    def verify(self, platform_id: str) -> bool:
        return True
