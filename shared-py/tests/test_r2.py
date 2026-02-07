from unittest.mock import patch, MagicMock

from shared_py.r2 import get_s3_client, upload_to_r2, download_from_r2
import shared_py.r2 as r2_module


class TestGetS3Client:
    def setup_method(self):
        # Reset cached client between tests
        r2_module._s3_client = None

    @patch("shared_py.r2.boto3.client")
    @patch.dict("os.environ", {
        "R2_ACCOUNT_ID": "acct-123",
        "R2_ACCESS_KEY_ID": "key-456",
        "R2_SECRET_ACCESS_KEY": "secret-789",
    })
    def test_creates_client_from_env(self, mock_client):
        get_s3_client()
        mock_client.assert_called_once_with(
            "s3",
            endpoint_url="https://acct-123.r2.cloudflarestorage.com",
            aws_access_key_id="key-456",
            aws_secret_access_key="secret-789",
            region_name="auto",
        )

    @patch("shared_py.r2.boto3.client")
    @patch.dict("os.environ", {
        "R2_ACCOUNT_ID": "acct-123",
        "R2_ACCESS_KEY_ID": "key-456",
        "R2_SECRET_ACCESS_KEY": "secret-789",
    })
    def test_caches_client(self, mock_client):
        client1 = get_s3_client()
        client2 = get_s3_client()
        assert client1 is client2
        mock_client.assert_called_once()


class TestUploadToR2:
    def setup_method(self):
        r2_module._s3_client = None

    @patch("shared_py.r2.get_s3_client")
    @patch.dict("os.environ", {"R2_BUCKET": "test-bucket"})
    def test_calls_put_object(self, mock_get_client):
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3

        upload_to_r2("key.jpg", b"data", "image/jpeg")
        mock_s3.put_object.assert_called_once_with(
            Bucket="test-bucket", Key="key.jpg", Body=b"data", ContentType="image/jpeg",
        )

    @patch("shared_py.r2.get_s3_client")
    @patch.dict("os.environ", {}, clear=True)
    def test_uses_default_bucket(self, mock_get_client):
        mock_s3 = MagicMock()
        mock_get_client.return_value = mock_s3

        upload_to_r2("key.jpg", b"data", "image/jpeg")
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "keda-jobs-prod"


class TestDownloadFromR2:
    def setup_method(self):
        r2_module._s3_client = None

    @patch("shared_py.r2.get_s3_client")
    @patch.dict("os.environ", {"R2_BUCKET": "test-bucket"})
    def test_calls_get_object(self, mock_get_client):
        mock_s3 = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = b"image-data"
        mock_s3.get_object.return_value = {"Body": mock_body}
        mock_get_client.return_value = mock_s3

        result = download_from_r2("images/photo.jpg")
        assert result == b"image-data"
        mock_s3.get_object.assert_called_once_with(Bucket="test-bucket", Key="images/photo.jpg")
