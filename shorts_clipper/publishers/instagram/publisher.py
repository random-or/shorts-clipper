import logging
import time
import requests
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime

from ..base import Publisher
from ..models import ClipMetadata, PublishResult
from shorts_clipper.core.settings import Settings

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
                res = requests.post(url, data={"reqtype": "fileupload"}, files={"fileToUpload": f}, timeout=120)
            if res.status_code != 200:
                raise RuntimeError(f"Catbox failed: {res.status_code}")
            return res.text.strip()
            
        def try_tmpfiles() -> str:
            url = "https://tmpfiles.org/api/v1/upload"
            with open(video_path, "rb") as f:
                res = requests.post(url, files={"file": f}, timeout=120)
            if res.status_code != 200:
                raise RuntimeError(f"Tmpfiles failed: {res.status_code}")
            data = res.json()
            # Convert https://tmpfiles.org/wiwl0qpA1I9R/test.mp4 to https://tmpfiles.org/dl/wiwl0qpA1I9R/test.mp4
            return data["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")
            
        def try_uguu() -> str:
            url = "https://uguu.se/upload.php"
            with open(video_path, "rb") as f:
                files = {"files[]": (video_path.name, f, "video/mp4")}
                res = requests.post(url, files=files, timeout=120)
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

    def publish(
        self,
        video_path: Path,
        metadata: ClipMetadata,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> PublishResult:
        token = self.settings.ig_access_token
        ig_id = self.settings.ig_account_id
        
        if not token or not ig_id:
            return PublishResult(platform=self.platform_name, success=False, error_message="Graph API credentials missing.")

        tags_str = " ".join([f"#{t}" for t in metadata.tags])
        caption = f"{metadata.title}\n\n{metadata.description}\n\n{tags_str}"
        
        try:
            # Step 1: Temporarily host the video
            video_url = self._upload_temp_video(video_path)
            log.info(f"Temporary public video URL: {video_url}")
            
            # Step 2: Create Media Container
            log.info("Initializing Reel upload via Graph API...")
            url = f"https://graph.instagram.com/v19.0/{ig_id}/media"
            payload = {
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption,
                "access_token": token
            }
            res = requests.post(url, data=payload, timeout=30)
            res_data = res.json()
            
            if "error" in res_data:
                raise RuntimeError(f"Graph API Error: {res_data['error']['message']}")
                
            creation_id = res_data.get("id")
            if not creation_id:
                raise RuntimeError(f"Failed to get creation_id: {res_data}")
                
            # Step 3: Check Status until FINISHED
            log.info(f"Container created ({creation_id}). Waiting for Meta to download and process the video...")
            status_url = f"https://graph.instagram.com/v19.0/{creation_id}?fields=status_code&access_token={token}"
            
            max_attempts = 60
            for attempt in range(max_attempts):
                status_res = requests.get(status_url, timeout=30).json()
                status = status_res.get("status_code")
                log.info(f"Processing status: {status}")
                if status == "FINISHED":
                    break
                elif status == "ERROR":
                    raise RuntimeError("Meta failed to process the video (Status: ERROR). Check the video format.")
                
                if progress_callback:
                    progress_callback(min(90, int(90 * (attempt / max_attempts))))
                time.sleep(5)
            else:
                raise RuntimeError("Timeout waiting for Meta to process the video.")
                
            # Step 4: Publish
            log.info("Processing complete. Publishing Reel to Instagram...")
            publish_url = f"https://graph.instagram.com/v19.0/{ig_id}/media_publish"
            pub_res = requests.post(publish_url, data={"creation_id": creation_id, "access_token": token}, timeout=30)
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

