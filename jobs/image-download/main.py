"""
image-download - Downloads images and uploads them to R2 object storage.

Pulls 'image-download' messages from NATS JetStream with an image URL and
optional HTTP headers, downloads the image, uploads to Cloudflare R2, and
publishes an 'image-downloaded' message with the R2 metadata.
"""

import os
import uuid
import logging
from urllib.parse import urlparse

import requests

from shared_py.nats_consumer import run_consumer
from shared_py.r2 import upload_to_r2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_image(url: str, headers: dict) -> tuple[bytes, str]:
    """Download image, return (content, content_type)."""
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "application/octet-stream")
    return resp.content, content_type


def build_r2_key(url: str) -> str:
    """Build the R2 object key with a UUID filename."""
    path = urlparse(url).path
    ext = os.path.splitext(path)[1]
    return f"images/{uuid.uuid4()}{ext}"


async def handle_event(data: dict, publish):
    """Handle an image-download message."""
    url = data.get("url")
    if not url:
        raise ValueError("Missing 'url' in event data")

    headers = data.get("headers", {})

    # Download
    image_bytes, content_type = download_image(url, headers)
    logger.info(f"Downloaded {len(image_bytes)} bytes, content-type={content_type}")

    # Upload to R2
    r2_key = build_r2_key(url)
    upload_to_r2(r2_key, image_bytes, content_type)
    logger.info(f"Upload complete: {r2_key}")

    # Publish image-downloaded event (r2_key only - bucket comes from env)
    await publish("image-downloaded", {"r2_key": r2_key})


if __name__ == "__main__":
    run_consumer(handler=handle_event, job_name="image-download")
