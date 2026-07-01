import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

from shorts_clipper.publishers import PublishingEngine, ClipMetadata, PublishResult, PublisherRegistry
from shorts_clipper.publishers.base import Publisher


class MockYouTubePublisher(Publisher):
    def __init__(self):
        self.auth_called = False
        self.publish_called = False
        self.verify_called = False
        self.should_fail = False
        self.should_verify_fail = False

    @property
    def platform_name(self) -> str:
        return "youtube"

    def authenticate(self) -> None:
        self.auth_called = True
        if self.should_fail:
            raise RuntimeError("YouTube auth failed")

    def publish(self, video_path, metadata, progress_callback=None):
        self.publish_called = True
        if self.should_fail:
            return PublishResult(self.platform_name, False, error_message="Upload failed")
        return PublishResult(self.platform_name, True, "http://yt", "yt123")

    def verify(self, platform_id: str) -> bool:
        self.verify_called = True
        if self.should_verify_fail:
            return False
        return True


class MockInstagramPublisher(Publisher):
    def __init__(self):
        self.auth_called = False
        self.publish_called = False
        self.verify_called = False
        self.should_fail = False
        self.fail_count = 0
        self.current_fails = 0

    @property
    def platform_name(self) -> str:
        return "instagram"

    def authenticate(self) -> None:
        self.auth_called = True

    def publish(self, video_path, metadata, progress_callback=None):
        self.publish_called = True
        if self.should_fail or self.current_fails < self.fail_count:
            self.current_fails += 1
            raise RuntimeError("Insta fail")
        return PublishResult(self.platform_name, True, "http://ig", "ig123")

    def verify(self, platform_id: str) -> bool:
        self.verify_called = True
        return True


@pytest.fixture(autouse=True)
def setup_registry():
    """Register mock publishers before each test, clear them after."""
    # Backup original publishers
    original = dict(PublisherRegistry._publishers)
    PublisherRegistry._publishers.clear()
    
    # Register mocks
    PublisherRegistry.register(MockYouTubePublisher)
    PublisherRegistry.register(MockInstagramPublisher)
    
    yield
    
    # Restore original publishers
    PublisherRegistry._publishers = original


def test_publisher_registry():
    # Verify that both are registered
    assert "youtube" in PublisherRegistry._publishers
    assert "instagram" in PublisherRegistry._publishers
    
    yt = PublisherRegistry.get_publisher("youtube")
    assert isinstance(yt, MockYouTubePublisher)
    assert yt.platform_name == "youtube"


def test_publishing_engine_success(tmp_path):
    engine = PublishingEngine(max_retries=1, base_backoff=0)
    video_path = tmp_path / "test_clip.mp4"
    video_path.touch()
    
    meta = ClipMetadata(title="Test", description="Test desc")
    
    results = engine.publish(video_path, meta, ["youtube", "instagram"])
    
    assert len(results) == 2
    assert results["youtube"].success
    assert results["instagram"].success
    
    manifest_path = tmp_path / "test_clip_publish_manifest.json"
    assert manifest_path.exists()
    
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
    
    assert manifest["overall_status"] == "SUCCESS"
    assert manifest["results"]["youtube"]["success"] is True
    assert manifest["results"]["instagram"]["success"] is True


def test_publishing_engine_partial_success(tmp_path):
    # Make instagram fail
    ig = PublisherRegistry.get_publisher("instagram")
    ig.should_fail = True
    PublisherRegistry._publishers["instagram"] = lambda: ig
    
    engine = PublishingEngine(max_retries=1, base_backoff=0)
    video_path = tmp_path / "test_clip2.mp4"
    video_path.touch()
    
    meta = ClipMetadata(title="Test", description="Test desc")
    
    results = engine.publish(video_path, meta, ["youtube", "instagram"])
    
    assert results["youtube"].success is True
    assert results["instagram"].success is False
    
    manifest_path = tmp_path / "test_clip2_publish_manifest.json"
    with open(manifest_path, "r") as f:
        manifest = json.load(f)
        
    assert manifest["overall_status"] == "PARTIAL_SUCCESS"


def test_publishing_engine_retry_logic(tmp_path):
    ig = PublisherRegistry.get_publisher("instagram")
    ig.fail_count = 2 # Fail twice, succeed on third
    PublisherRegistry._publishers["instagram"] = lambda: ig
    
    engine = PublishingEngine(max_retries=3, base_backoff=0)
    video_path = tmp_path / "test_clip3.mp4"
    video_path.touch()
    
    meta = ClipMetadata(title="Test", description="Test desc")
    
    results = engine.publish(video_path, meta, ["instagram"])
    
    assert results["instagram"].success is True
    assert results["instagram"].retry_count == 2 # 0-indexed, so 0,1,2 = 3rd attempt


def test_failure_isolation(tmp_path):
    # Make youtube auth fail
    yt = PublisherRegistry.get_publisher("youtube")
    yt.should_fail = True
    PublisherRegistry._publishers["youtube"] = lambda: yt
    
    engine = PublishingEngine(max_retries=1, base_backoff=0)
    video_path = tmp_path / "test_clip4.mp4"
    video_path.touch()
    
    meta = ClipMetadata(title="Test", description="Test desc")
    
    results = engine.publish(video_path, meta, ["youtube", "instagram"])
    
    # YouTube should fail
    assert results["youtube"].success is False
    # Instagram should still succeed
    assert results["instagram"].success is True


class MockNewPublisher(Publisher):
    @property
    def platform_name(self) -> str: return "tiktok"
    def authenticate(self) -> None: pass
    def publish(self, vp, meta, cb=None): return PublishResult("tiktok", True)
    def verify(self, pid: str) -> bool: return True


def test_adding_new_publisher_without_modifying_pipeline(tmp_path):
    PublisherRegistry.register(MockNewPublisher)
    
    engine = PublishingEngine(max_retries=1, base_backoff=0)
    video_path = tmp_path / "test_clip5.mp4"
    video_path.touch()
    
    meta = ClipMetadata(title="Test", description="Test desc")
    
    results = engine.publish(video_path, meta, ["tiktok"])
    
    assert results["tiktok"].success is True
