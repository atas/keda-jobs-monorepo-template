"""
image-resize - Resizes images and uploads them to R2 object storage.

Pulls 'image-downloaded' messages from NATS JetStream with R2 metadata,
downloads the image from R2, resizes to a max dimension (200px), and uploads the
resized image to R2 under images_resized/.
"""

import io
import logging

from PIL import Image

from shared_py.nats_consumer import run_consumer
from shared_py.r2 import download_from_r2, upload_to_r2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_DIMENSION = 200


def build_resized_key(original_key: str) -> str:
    """Swap images/ prefix with images_resized/."""
    if original_key.startswith("images/"):
        return "images_resized/" + original_key[len("images/"):]
    return "images_resized/" + original_key


def resize_image(image_bytes: bytes, max_dim: int = MAX_DIMENSION) -> tuple[bytes, int, int, str]:
    """Resize image to fit within max_dim, maintaining aspect ratio.

    Returns (resized_bytes, width, height, format).
    Only shrinks — images already within max_dim are returned as-is.
    """
    img = Image.open(io.BytesIO(image_bytes))
    fmt = img.format or "PNG"
    w, h = img.size

    if w <= max_dim and h <= max_dim:
        return image_bytes, w, h, fmt

    img.thumbnail((max_dim, max_dim))
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    new_w, new_h = img.size
    return buf.getvalue(), new_w, new_h, fmt


FORMAT_TO_CONTENT_TYPE = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "GIF": "image/gif",
    "WEBP": "image/webp",
}


async def handle_event(data: dict, publish):
    """Handle an image-downloaded message."""
    r2_key = data.get("r2_key")
    if not r2_key:
        raise ValueError("Missing 'r2_key' in event data")

    # Download from R2
    image_bytes = download_from_r2(r2_key)
    logger.info(f"Downloaded {len(image_bytes)} bytes from R2: {r2_key}")

    # Resize
    resized_bytes, new_w, new_h, fmt = resize_image(image_bytes)
    logger.info(f"Resized to {new_w}x{new_h} ({len(resized_bytes)} bytes)")

    # Upload resized image
    resized_key = build_resized_key(r2_key)
    content_type = FORMAT_TO_CONTENT_TYPE.get(fmt, "application/octet-stream")
    upload_to_r2(resized_key, resized_bytes, content_type)

    logger.info(f"Upload complete: {resized_key}")


if __name__ == "__main__":
    run_consumer(handler=handle_event, job_name="image-resize")
