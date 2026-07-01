from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shorts_clipper.core.settings import Settings
from shorts_clipper.publishers.instagram.publisher import InstagramGraphPublisher


@patch("shorts_clipper.publishers.instagram.publisher.Settings.from_env")
@patch("shorts_clipper.publishers.instagram.publisher.os.link")
def test_instagram_publisher_uses_public_url(mock_link, mock_settings_from_env):
    # Mock settings with PUBLIC_URL but NO use_temp_hosts
    mock_settings = MagicMock(spec=Settings)
    mock_settings.use_temp_hosts = False
    mock_settings.public_url = "https://my-app.railway.app/"
    mock_settings_from_env.return_value = mock_settings

    publisher = InstagramGraphPublisher()
    video_path = Path("outputs/clip test123.mp4")

    url = publisher._get_video_url(video_path)
    assert url.startswith("https://my-app.railway.app/clips/ig_hosted/clip%20test123_")
    assert url.endswith(".mp4")
    mock_link.assert_called_once()


@patch("shorts_clipper.publishers.instagram.publisher.Settings.from_env")
def test_instagram_publisher_requires_public_url(mock_settings_from_env):
    mock_settings = MagicMock(spec=Settings)
    mock_settings.use_temp_hosts = False
    mock_settings.public_url = None
    mock_settings_from_env.return_value = mock_settings

    publisher = InstagramGraphPublisher()
    video_path = Path("outputs/clip_test123.mp4")

    with pytest.raises(RuntimeError) as exc_info:
        publisher._get_video_url(video_path)

    assert "PUBLIC_URL must be set" in str(exc_info.value)


@patch("shorts_clipper.publishers.instagram.publisher.Settings.from_env")
@patch.object(InstagramGraphPublisher, "_upload_temp_video")
def test_instagram_publisher_fallback_to_temp_hosts(mock_upload, mock_settings_from_env):
    mock_settings = MagicMock(spec=Settings)
    mock_settings.use_temp_hosts = True
    mock_settings.public_url = None
    mock_settings_from_env.return_value = mock_settings

    mock_upload.return_value = "https://catbox.moe/mock_url.mp4"

    publisher = InstagramGraphPublisher()
    video_path = Path("outputs/clip_test123.mp4")

    url = publisher._get_video_url(video_path)
    assert url == "https://catbox.moe/mock_url.mp4"
    mock_upload.assert_called_once_with(video_path)
