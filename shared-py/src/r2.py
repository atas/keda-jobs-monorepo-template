"""Shared Cloudflare R2 (S3-compatible) helpers.

All functions use env vars for defaults:
- R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY for auth
- R2_BUCKET for the bucket name
"""

import os

import boto3

# Module-level cached client
_s3_client = None


def get_s3_client():
    """Get or create a cached S3 client using env vars."""
    global _s3_client
    if _s3_client is None:
        account_id = os.environ.get("R2_ACCOUNT_ID")
        _s3_client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ.get("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY"),
            region_name="auto",
        )
    return _s3_client


def upload_to_r2(key: str, body: bytes, content_type: str):
    """Upload bytes to R2. Uses R2_BUCKET env var."""
    bucket = os.environ.get("R2_BUCKET", "keda-jobs-prod")
    get_s3_client().put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)


def download_from_r2(key: str) -> bytes:
    """Download an object from R2. Uses R2_BUCKET env var."""
    bucket = os.environ.get("R2_BUCKET", "keda-jobs-prod")
    response = get_s3_client().get_object(Bucket=bucket, Key=key)
    return response["Body"].read()
