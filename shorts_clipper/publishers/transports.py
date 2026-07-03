import abc
import logging
import os
import shutil
import threading
import time
import urllib.parse
import uuid
from pathlib import Path

import requests

from shorts_clipper.core.settings import Settings

log = logging.getLogger(__name__)


class StorageProvider(abc.ABC):
    @abc.abstractmethod
    def upload(self, video_path: Path) -> str:
        """Upload a video and return a publicly accessible URL."""
        pass


class TempHostTransport(StorageProvider):
    def upload(self, video_path: Path) -> str:
        log.info("Uploading video to temporary host...")

        def try_catbox() -> str:
            url = os.environ.get("CATBOX_URL", "https://litterbox.catbox.moe/resources/internals/api.php")
            if not url:
                raise RuntimeError("CATBOX_URL not set")
            with open(video_path, "rb") as f:
                res = requests.post(
                    url, data={"reqtype": "fileupload", "time": "1h"}, files={"fileToUpload": f}, timeout=600
                )
            if res.status_code != 200:
                raise RuntimeError(f"Catbox failed: {res.status_code}")
            return res.text.strip()

        def try_tmpfiles() -> str:
            url = os.environ.get("TMPFILES_URL", "https://tmpfiles.org/api/v1/upload")
            if not url:
                raise RuntimeError("TMPFILES_URL not set")
            with open(video_path, "rb") as f:
                res = requests.post(url, files={"file": f}, timeout=600)
            if res.status_code != 200:
                raise RuntimeError(f"Tmpfiles failed: {res.status_code}")
            data = res.json()
            return data["data"]["url"].replace("tmpfiles.org/", "tmpfiles.org/dl/")

        def try_uguu() -> str:
            url = os.environ.get("UGUU_URL", "https://uguu.se/api.php?d=upload-tool")
            if not url:
                raise RuntimeError("UGUU_URL not set")
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


class LocalTunnelTransport(StorageProvider):
    def __init__(self, public_url: str):
        self.public_url = public_url

    def upload(self, video_path: Path) -> str:
        hosted_dir = video_path.parent / "ig_hosted"
        hosted_dir.mkdir(exist_ok=True)
        unique_name = f"{video_path.stem}_{uuid.uuid4().hex[:8]}{video_path.suffix}"
        unique_path = hosted_dir / unique_name

        try:
            os.link(video_path, unique_path)
        except OSError:
            shutil.copy2(video_path, unique_path)

        def _cleanup_link(p: Path) -> None:
            time.sleep(3600)
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass

        threading.Thread(target=_cleanup_link, args=(unique_path,), daemon=True).start()

        base_url = self.public_url.rstrip("/")
        encoded_name = urllib.parse.quote(unique_name)
        url = f"{base_url}/clips/ig_hosted/{encoded_name}"
        log.info(f"Using self-hosted video URL: {url}")
        return url


def get_storage_provider(settings: Settings) -> StorageProvider:
    if settings.use_temp_hosts:
        log.warning("Using deprecated temporary hosts for video upload. Set PUBLIC_URL instead.")
        return TempHostTransport()

    if not settings.public_url:
        raise RuntimeError(
            "PUBLIC_URL must be set in settings/env to publish natively, or set SHORTS_USE_TEMP_HOSTS=true."
        )
    return LocalTunnelTransport(public_url=settings.public_url)
