from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shorts_clipper.core.settings import Settings
from shorts_clipper.publishers.transports import (
    LocalTunnelTransport,
    TempHostTransport,
    get_storage_provider,
)


@patch("shorts_clipper.publishers.transports.os.link")
def test_transports_local_tunnel(mock_link):
    transport = LocalTunnelTransport(public_url="https://my-app.railway.app/")
    video_path = Path("outputs/clip test123.mp4")

    url = transport.upload(video_path)
    assert url.startswith("https://my-app.railway.app/clips/ig_hosted/clip%20test123_")
    assert url.endswith(".mp4")
    mock_link.assert_called_once()


def test_transports_get_provider_requires_public_url():
    mock_settings = MagicMock(spec=Settings)
    mock_settings.use_temp_hosts = False
    mock_settings.public_url = None

    with pytest.raises(RuntimeError) as exc_info:
        get_storage_provider(mock_settings)

    assert "PUBLIC_URL must be set" in str(exc_info.value)


@patch.object(TempHostTransport, "upload")
def test_transports_get_provider_fallback(mock_upload):
    mock_settings = MagicMock(spec=Settings)
    mock_settings.use_temp_hosts = True
    mock_settings.public_url = None

    provider = get_storage_provider(mock_settings)
    assert isinstance(provider, TempHostTransport)

    mock_upload.return_value = "https://catbox.moe/mock_url.mp4"
    url = provider.upload(Path("outputs/clip_test123.mp4"))
    assert url == "https://catbox.moe/mock_url.mp4"
    mock_upload.assert_called_once()
