import logging
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime

from ..base import Publisher
from ..models import ClipMetadata, PublishResult
from .auth import get_youtube_service
from .uploader import upload_short

log = logging.getLogger(__name__)

class YouTubePublisher(Publisher):
    """Handles publishing vertical clips to YouTube Shorts."""

    @property
    def platform_name(self) -> str:
        return "youtube"

    def authenticate(self) -> None:
        """Authenticate with YouTube to ensure credentials are valid."""
        get_youtube_service()
        log.info("YouTube authentication verified.")

    def publish(
        self,
        video_path: Path,
        metadata: ClipMetadata,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> PublishResult:
        try:
            video_id = upload_short(
                video_path=video_path,
                title=metadata.title,
                description=metadata.description,
                tags=metadata.tags,
                privacy_status=metadata.privacy_status,
                progress_callback=progress_callback,
            )
            return PublishResult(
                platform=self.platform_name,
                success=True,
                url=f"https://youtube.com/shorts/{video_id}" if video_id else None,
                platform_id=video_id,
                published_at=datetime.utcnow().isoformat() + "Z",
            )
        except Exception as e:
            log.error(f"YouTube publishing failed: {e}")
            return PublishResult(
                platform=self.platform_name,
                success=False,
                error_message=str(e),
            )

    def verify(self, platform_id: str) -> bool:
        """Verify that the YouTube video is accessible."""
        try:
            youtube = get_youtube_service()
            request = youtube.videos().list(part="status", id=platform_id)
            response = request.execute()
            items = response.get("items", [])
            if items:
                return True
            return False
        except Exception as e:
            log.error(f"Failed to verify YouTube upload: {e}")
            return False
