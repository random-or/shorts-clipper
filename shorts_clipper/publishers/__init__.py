from .manager import PublishingEngine
from .models import ClipMetadata, PublishResult
from .registry import PublisherRegistry
from .youtube.publisher import YouTubePublisher
from .instagram.publisher import InstagramGraphPublisher

PublisherRegistry.register(YouTubePublisher)
PublisherRegistry.register(InstagramGraphPublisher)

__all__ = [
    "PublishingEngine",
    "ClipMetadata",
    "PublishResult",
    "PublisherRegistry",
]
