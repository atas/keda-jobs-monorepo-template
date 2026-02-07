import re
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from main import build_r2_key, download_image, handle_event


UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class TestBuildR2Key:
    def test_produces_uuid_key_with_extension(self):
        key = build_r2_key("https://example.com/photo.jpg")
        assert key.startswith("images/")
        assert key.endswith(".jpg")
        uuid_part = key[len("images/"):-len(".jpg")]
        assert UUID_RE.match(uuid_part)

    def test_preserves_extension_from_url(self):
        key = build_r2_key("https://example.com/image.png")
        assert key.endswith(".png")

    def test_no_extension_when_url_has_none(self):
        key = build_r2_key("https://example.com/image")
        uuid_part = key[len("images/"):]
        assert UUID_RE.match(uuid_part)


class TestDownloadImage:
    @patch("main.requests.get")
    def test_returns_content_and_type(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.content = b"fake-image-data"
        mock_resp.headers = {"Content-Type": "image/png"}
        mock_get.return_value = mock_resp

        content, content_type = download_image("https://example.com/img.png", {})
        assert content == b"fake-image-data"
        assert content_type == "image/png"
        mock_get.assert_called_once_with("https://example.com/img.png", headers={}, timeout=60)

    @patch("main.requests.get")
    def test_passes_custom_headers(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.content = b"data"
        mock_resp.headers = {"Content-Type": "image/jpeg"}
        mock_get.return_value = mock_resp

        headers = {"Referer": "https://example.com", "Cookie": "session=abc"}
        download_image("https://example.com/img.jpg", headers)
        mock_get.assert_called_once_with("https://example.com/img.jpg", headers=headers, timeout=60)

    @patch("main.requests.get")
    def test_defaults_content_type(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.content = b"data"
        mock_resp.headers = {}
        mock_get.return_value = mock_resp

        _, content_type = download_image("https://example.com/file", {})
        assert content_type == "application/octet-stream"


class TestHandleEvent:
    @pytest.mark.asyncio
    @patch("main.upload_to_r2")
    @patch("main.requests.get")
    async def test_successful_download_and_upload(self, mock_get, mock_upload):
        mock_resp = MagicMock()
        mock_resp.content = b"fake-image-data"
        mock_resp.headers = {"Content-Type": "image/png"}
        mock_get.return_value = mock_resp

        mock_publish = AsyncMock()
        await handle_event({"url": "https://example.com/photo.png"}, mock_publish)

        mock_upload.assert_called_once()
        call_args = mock_upload.call_args[0]
        assert call_args[0].startswith("images/")
        assert call_args[0].endswith(".png")
        assert call_args[1] == b"fake-image-data"
        assert call_args[2] == "image/png"

    @pytest.mark.asyncio
    async def test_missing_url_raises(self):
        mock_publish = AsyncMock()
        with pytest.raises(ValueError, match="Missing 'url'"):
            await handle_event({}, mock_publish)

    @pytest.mark.asyncio
    @patch("main.requests.get")
    async def test_download_failure_raises(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")

        mock_publish = AsyncMock()
        with pytest.raises(Exception, match="Connection refused"):
            await handle_event({"url": "https://example.com/img.png"}, mock_publish)

    @pytest.mark.asyncio
    @patch("main.upload_to_r2")
    @patch("main.requests.get")
    async def test_publishes_event(self, mock_get, mock_upload):
        mock_resp = MagicMock()
        mock_resp.content = b"fake-image-data"
        mock_resp.headers = {"Content-Type": "image/jpeg"}
        mock_get.return_value = mock_resp

        mock_publish = AsyncMock()
        await handle_event({"url": "https://example.com/pic.jpg"}, mock_publish)

        mock_publish.assert_called_once()
        subject, data = mock_publish.call_args[0]
        assert subject == "image-downloaded"
        assert data["r2_key"].startswith("images/")
