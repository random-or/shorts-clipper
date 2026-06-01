"""Base publisher adapters interface."""

from abc import ABC, abstractmethod
from pathlib import Path


class PublisherAdapter(ABC):
    """Abstract base class representing a generic vertical video publisher."""

    @abstractmethod
    def publish(self, video_path: Path, title: str, description: str, **kwargs) -> bool:
        """
        Publish a vertical video clip to the destination platform.

        Args:
            video_path: Path to the MP4 file to upload.
            title: Title of the video.
            description: Description / caption for the post.

        Returns:
            True on successful publishing, False otherwise.
        """
        pass
