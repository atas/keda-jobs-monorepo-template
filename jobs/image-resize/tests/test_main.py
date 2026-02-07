import io
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from PIL import Image

from main import resize_image, build_resized_key, handle_event


def _make_test_image(width, height, fmt="PNG"):
    """Create a test image and return its bytes."""
    img = Image.new("RGB", (width, height), color="blue")
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


class TestResizeImage:
    def test_shrinks_large_image(self):
        data = _make_test_image(2000, 1000)
        resized, w, h, fmt = resize_image(data, max_dim=200)
        assert w == 200
        assert h == 100
        assert fmt == "PNG"
        assert len(resized) < len(data)

    def test_shrinks_tall_image(self):
        data = _make_test_image(500, 2000)
        resized, w, h, fmt = resize_image(data, max_dim=200)
        assert w == 50
        assert h == 200

    def test_no_resize_if_within_max(self):
        data = _make_test_image(150, 100)
        resized, w, h, fmt = resize_image(data, max_dim=200)
        assert w == 150
        assert h == 100
        assert resized == data

    def test_no_resize_if_exact_max(self):
        data = _make_test_image(200, 150)
        resized, w, h, fmt = resize_image(data, max_dim=200)
        assert w == 200
        assert h == 150
        assert resized == data

    def test_preserves_jpeg_format(self):
        data = _make_test_image(2000, 1000, "JPEG")
        resized, w, h, fmt = resize_image(data, max_dim=200)
        assert fmt == "JPEG"
        img = Image.open(io.BytesIO(resized))
        assert img.format == "JPEG"

    def test_square_image(self):
        data = _make_test_image(400, 400)
        resized, w, h, fmt = resize_image(data, max_dim=200)
        assert w == 200
        assert h == 200


class TestBuildResizedKey:
    def test_swaps_images_prefix(self):
        assert build_resized_key("images/abc.jpg") == "images_resized/abc.jpg"

    def test_handles_no_images_prefix(self):
        assert build_resized_key("other/path/photo.jpg") == \
            "images_resized/other/path/photo.jpg"

    def test_only_swaps_leading_prefix(self):
        assert build_resized_key("images/abc/images/photo.jpg") == \
            "images_resized/abc/images/photo.jpg"


class TestHandleEvent:
    @pytest.mark.asyncio
    @patch("main.upload_to_r2")
    @patch("main.download_from_r2")
    async def test_successful_resize_and_upload(self, mock_download, mock_upload):
        test_image = _make_test_image(2000, 1000)
        mock_download.return_value = test_image

        mock_publish = AsyncMock()
        await handle_event({"r2_key": "images/abc123.png"}, mock_publish)

        mock_download.assert_called_once_with("images/abc123.png")
        mock_upload.assert_called_once()
        call_args = mock_upload.call_args[0]
        assert call_args[0] == "images_resized/abc123.png"
        assert call_args[2] == "image/png"
        uploaded = Image.open(io.BytesIO(call_args[1]))
        assert uploaded.size == (200, 100)
        mock_publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_r2_key_raises(self):
        mock_publish = AsyncMock()
        with pytest.raises(ValueError, match="Missing"):
            await handle_event({}, mock_publish)

    @pytest.mark.asyncio
    @patch("main.upload_to_r2")
    @patch("main.download_from_r2")
    async def test_skips_resize_for_small_image(self, mock_download, mock_upload):
        test_image = _make_test_image(150, 100)
        mock_download.return_value = test_image

        mock_publish = AsyncMock()
        await handle_event({"r2_key": "images/abc123-small.png"}, mock_publish)

        call_args = mock_upload.call_args[0]
        uploaded = Image.open(io.BytesIO(call_args[1]))
        assert uploaded.size == (150, 100)
