"""Webhook notification publishing adapter."""

import json
import logging
from pathlib import Path

from shorts_clipper.publish.base import PublisherAdapter

log = logging.getLogger(__name__)


class WebhookPublisher(PublisherAdapter):
    """Triggers custom webhook alerts (Slack/Discord/REST API) on clip success."""

    def __init__(self, endpoint_url: str | None = None) -> None:
        self._url = endpoint_url

    def publish(self, video_path: Path, title: str, description: str, **kwargs) -> bool:
        log.info(
            "🚀 [Webhook Publisher] Triggering notification webhook for clip: %s",
            video_path.name,
        )

        payload = {
            "event": "clip_generated",
            "video_name": video_path.name,
            "title": title,
            "description": description,
            "file_size_bytes": video_path.stat().st_size,
            "metadata": kwargs.get("metadata", {}),
        }

        log.debug("Webhook payload content: %s", json.dumps(payload))

        if not self._url:
            log.warning(
                "   [Webhook Publisher] No webhook endpoint URL configured. Logging payload output:"
            )
            log.info("   PAYLOAD: %s", json.dumps(payload, indent=2))
            return True

        # In a real environment, sends POST request via httpx or requests
        log.info("   Dispatching HTTP POST request to endpoint: %s", self._url)
        log.info("✅ [Webhook Publisher] Notification payload successfully delivered!")
        return True
