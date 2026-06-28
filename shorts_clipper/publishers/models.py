from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

@dataclass
class ClipMetadata:
    """Universal metadata object for a clip."""
    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    privacy_status: str = "private"
    language: str = "en"


@dataclass
class PublishResult:
    """Result of a publishing attempt."""
    platform: str
    success: bool
    url: Optional[str] = None
    platform_id: Optional[str] = None
    published_at: Optional[str] = None
    retry_count: int = 0
    error_message: Optional[str] = None
