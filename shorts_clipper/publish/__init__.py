"""Publisher adapters module initialization."""

from shorts_clipper.publish.base import PublisherAdapter
from shorts_clipper.publish.instagram import InstagramPublisher
from shorts_clipper.publish.webhook import WebhookPublisher
from shorts_clipper.publish.youtube import YouTubePublisher

__all__ = [
    "PublisherAdapter",
    "InstagramPublisher",
    "WebhookPublisher",
    "YouTubePublisher",
]
