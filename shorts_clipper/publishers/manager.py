import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import ClipMetadata, PublishResult
from .registry import PublisherRegistry

log = logging.getLogger(__name__)


class PublishingEngine:
    """Core engine responsible for multi-platform publishing."""

    def __init__(
        self,
        max_retries: int = 3,
        base_backoff: int = 2,
    ):
        self.max_retries = max_retries
        self.base_backoff = base_backoff

    def publish(
        self,
        video_path: Path,
        metadata: ClipMetadata,
        platforms: List[str],
    ) -> Dict[str, PublishResult]:
        """
        Publish a video to multiple platforms independently.

        Args:
            video_path: Path to the video file.
            metadata: Universal metadata for the clip.
            platforms: List of platform names to publish to.

        Returns:
            A dictionary mapping platform names to their PublishResult.
        """
        results: Dict[str, PublishResult] = {}
        log.info(f"🚀 PublishingEngine started for {len(platforms)} platforms: {platforms}")

        for platform_name in platforms:
            try:
                publisher = PublisherRegistry.get_publisher(platform_name)
            except ValueError as e:
                log.error(f"❌ Could not initialize publisher for {platform_name}: {e}")
                results[platform_name] = PublishResult(
                    platform=platform_name,
                    success=False,
                    error_message=str(e),
                )
                continue

            # Attempt authentication first
            try:
                log.info(f"🔑 Authenticating for {platform_name}...")
                publisher.authenticate()
            except Exception as e:
                log.error(f"❌ Authentication failed for {platform_name}: {e}")
                results[platform_name] = PublishResult(
                    platform=platform_name,
                    success=False,
                    error_message=f"Auth failed: {e}",
                )
                continue

            # Retry loop for publishing
            result = None
            for attempt in range(1, self.max_retries + 1):
                try:
                    log.info(
                        f"📤 Publishing to {platform_name} (Attempt {attempt}/{self.max_retries})..."
                    )
                    
                    result = publisher.publish(video_path, metadata)
                    result.retry_count = attempt - 1
                    
                    if result.success:
                        # Optional Verification
                        try:
                            if result.platform_id and publisher.verify(result.platform_id):
                                log.info(f"✅ Verified upload for {platform_name}!")
                            else:
                                log.warning(f"⚠️ Verification inconclusive for {platform_name}")
                        except Exception as ve:
                            log.warning(f"⚠️ Verification check failed for {platform_name}: {ve}")
                        
                        log.info(f"✅ Successfully published to {platform_name}!")
                        break
                    else:
                        log.warning(f"⚠️ Publishing to {platform_name} returned failure: {result.error_message}")
                except Exception as e:
                    log.warning(f"⚠️ Publishing attempt {attempt} to {platform_name} threw an error: {e}")
                    result = PublishResult(
                        platform=platform_name,
                        success=False,
                        retry_count=attempt - 1,
                        error_message=str(e),
                    )

                if attempt < self.max_retries:
                    wait_time = self.base_backoff ** attempt
                    log.info(f"⏳ Waiting {wait_time}s before retrying {platform_name}...")
                    time.sleep(wait_time)

            results[platform_name] = result

        # Generate manifest
        self._generate_manifest(video_path, metadata, results)
        
        return results

    def _generate_manifest(
        self,
        video_path: Path,
        metadata: ClipMetadata,
        results: Dict[str, PublishResult],
    ) -> None:
        """Generates a publish_manifest.json file in the output directory."""
        manifest_path = video_path.with_name(f"{video_path.stem}_publish_manifest.json")
        
        platforms_requested = list(results.keys())
        successful = [p for p, r in results.items() if r.success]
        
        if len(successful) == len(platforms_requested):
            overall_status = "SUCCESS"
        elif len(successful) > 0:
            overall_status = "PARTIAL_SUCCESS"
        else:
            overall_status = "FAILED"

        manifest_data = {
            "clip_id": video_path.stem,
            "render_timestamp": datetime.utcnow().isoformat() + "Z",
            "video_path": str(video_path.resolve()),
            "metadata": {
                "title": metadata.title,
                "description": metadata.description,
                "tags": metadata.tags,
                "language": metadata.language,
            },
            "platforms_requested": platforms_requested,
            "overall_status": overall_status,
            "results": {
                platform: {
                    "success": result.success,
                    "url": result.url,
                    "platform_id": result.platform_id,
                    "published_at": result.published_at,
                    "retry_attempts": result.retry_count,
                    "error_message": result.error_message,
                }
                for platform, result in results.items()
            },
        }

        try:
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            log.info(f"📄 Generated publish manifest: {manifest_path}")
        except Exception as e:
            log.error(f"❌ Failed to generate publish manifest: {e}")
