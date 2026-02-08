"""
Unit tests for core/s3.py module.

Tests S3 client initialization, upload/download functions, and error handling.
"""

import os
import pytest
from unittest.mock import patch, MagicMock, Mock
from botocore.exceptions import ClientError, BotoCoreError

# Set up test environment variables before importing s3 module
os.environ.setdefault('POSTGRES_USER', 'test_user')
os.environ.setdefault('POSTGRES_PASSWORD', 'test_password')
os.environ.setdefault('POSTGRES_DB', 'test_db')
os.environ.setdefault('VECTOR_POSTGRES_DB', 'test_vector_db')
os.environ.setdefault('S3_ENDPOINT', 'https://test.s3.com')
os.environ.setdefault('S3_ACCESS_KEY', 'test_access_key')
os.environ.setdefault('S3_SECRET_KEY', 'test_secret_key')
os.environ.setdefault('S3_BUCKET', 'test_bucket')

from core.s3 import (
    get_s3_client,
    upload_image,
    download_image,
    S3Error,
    S3UploadError,
    S3DownloadError,
    S3ConnectionError
)


class TestS3Exceptions:
    """Test custom S3 exception classes."""
    
    def test_s3_error_is_exception(self):
        """Test that S3Error is an Exception."""
        assert issubclass(S3Error, Exception)
    
    def test_s3_upload_error_is_s3_error(self):
        """Test that S3UploadError inherits from S3Error."""
        assert issubclass(S3UploadError, S3Error)
    
    def test_s3_download_error_is_s3_error(self):
        """Test that S3DownloadError inherits from S3Error."""
        assert issubclass(S3DownloadError, S3Error)
    
    def test_s3_connection_error_is_s3_error(self):
        """Test that S3ConnectionError inherits from S3Error."""
        assert issubclass(S3ConnectionError, S3Error)


class TestGetS3Client:
    """Test S3 client initialization."""
    
    @patch('core.s3.boto3.client')
    def test_get_s3_client_creates_client(self, mock_boto_client):
        """Test that get_s3_client creates a boto3 S3 client."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        result = get_s3_client()
        
        assert result == mock_client
        mock_boto_client.assert_called_once()
    
    @patch('core.s3.boto3.client')
    def test_get_s3_client_uses_correct_parameters(self, mock_boto_client):
        """Test that get_s3_client uses correct configuration parameters."""
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        get_s3_client()
        
        # Verify boto3.client was called with correct parameters
        call_args = mock_boto_client.call_args
        assert call_args[0][0] == 's3'
        assert 'endpoint_url' in call_args[1]
        assert 'aws_access_key_id' in call_args[1]
        assert 'aws_secret_access_key' in call_args[1]
        assert 'region_name' in call_args[1]
        assert 'config' in call_args[1]
    
    @patch('core.s3.boto3.client')
    def test_get_s3_client_raises_on_error(self, mock_boto_client):
        """Test that get_s3_client raises S3ConnectionError on failure."""
        mock_boto_client.side_effect = Exception("Connection failed")
        
        with pytest.raises(S3ConnectionError) as exc_info:
            get_s3_client()
        
        assert "Failed to create S3 client" in str(exc_info.value)


class TestUploadImage:
    """Test image upload functionality."""
    
    @patch('core.s3.get_s3_client')
    def test_upload_image_success(self, mock_get_client):
        """Test successful image upload."""
        # Setup mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Test data
        file_data = b"fake image data"
        object_name = "test/image.jpg"
        
        # Execute
        result = upload_image(file_data, object_name)
        
        # Verify
        mock_client.put_object.assert_called_once()
        call_args = mock_client.put_object.call_args[1]
        assert call_args['Bucket'] == 'test_bucket'
        assert call_args['Key'] == object_name
        assert call_args['Body'] == file_data
        assert call_args['ContentType'] == 'image/jpeg'
        
        # Verify URL format
        assert 'test_bucket' in result
        assert object_name in result
    
    @patch('core.s3.get_s3_client')
    def test_upload_image_custom_content_type(self, mock_get_client):
        """Test image upload with custom content type."""
        # Setup mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Test data
        file_data = b"fake image data"
        object_name = "test/image.png"
        content_type = "image/png"
        
        # Execute
        upload_image(file_data, object_name, content_type)
        
        # Verify content type
        call_args = mock_client.put_object.call_args[1]
        assert call_args['ContentType'] == content_type
    
    def test_upload_image_empty_data_raises_error(self):
        """Test that upload_image raises ValueError for empty data."""
        with pytest.raises(ValueError) as exc_info:
            upload_image(b"", "test/image.jpg")
        
        assert "file_data cannot be empty" in str(exc_info.value)
    
    def test_upload_image_empty_object_name_raises_error(self):
        """Test that upload_image raises ValueError for empty object name."""
        with pytest.raises(ValueError) as exc_info:
            upload_image(b"data", "")
        
        assert "object_name cannot be empty" in str(exc_info.value)
    
    def test_upload_image_whitespace_object_name_raises_error(self):
        """Test that upload_image raises ValueError for whitespace-only object name."""
        with pytest.raises(ValueError) as exc_info:
            upload_image(b"data", "   ")
        
        assert "object_name cannot be empty" in str(exc_info.value)
    
    @patch('core.s3.get_s3_client')
    def test_upload_image_client_error(self, mock_get_client):
        """Test that upload_image raises S3UploadError on ClientError."""
        # Setup mock
        mock_client = MagicMock()
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'Access denied'
            }
        }
        mock_client.put_object.side_effect = ClientError(error_response, 'PutObject')
        mock_get_client.return_value = mock_client
        
        # Execute and verify
        with pytest.raises(S3UploadError) as exc_info:
            upload_image(b"data", "test/image.jpg")
        
        assert "Failed to upload image to S3" in str(exc_info.value)
    
    @patch('core.s3.get_s3_client')
    def test_upload_image_botocore_error(self, mock_get_client):
        """Test that upload_image raises S3UploadError on BotoCoreError."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.put_object.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client
        
        # Execute and verify
        with pytest.raises(S3UploadError):
            upload_image(b"data", "test/image.jpg")
    
    @patch('core.s3.get_s3_client')
    def test_upload_image_unexpected_error(self, mock_get_client):
        """Test that upload_image raises S3UploadError on unexpected error."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.put_object.side_effect = Exception("Unexpected error")
        mock_get_client.return_value = mock_client
        
        # Execute and verify
        with pytest.raises(S3UploadError):
            upload_image(b"data", "test/image.jpg")


class TestDownloadImage:
    """Test image download functionality."""
    
    @patch('core.s3.get_s3_client')
    def test_download_image_success(self, mock_get_client):
        """Test successful image download."""
        # Setup mock
        mock_client = MagicMock()
        mock_body = MagicMock()
        mock_body.read.return_value = b"fake image data"
        mock_client.get_object.return_value = {'Body': mock_body}
        mock_get_client.return_value = mock_client
        
        # Test data
        object_name = "test/image.jpg"
        
        # Execute
        result = download_image(object_name)
        
        # Verify
        mock_client.get_object.assert_called_once()
        call_args = mock_client.get_object.call_args[1]
        assert call_args['Bucket'] == 'test_bucket'
        assert call_args['Key'] == object_name
        assert result == b"fake image data"
    
    def test_download_image_empty_object_name_raises_error(self):
        """Test that download_image raises ValueError for empty object name."""
        with pytest.raises(ValueError) as exc_info:
            download_image("")
        
        assert "object_name cannot be empty" in str(exc_info.value)
    
    def test_download_image_whitespace_object_name_raises_error(self):
        """Test that download_image raises ValueError for whitespace-only object name."""
        with pytest.raises(ValueError) as exc_info:
            download_image("   ")
        
        assert "object_name cannot be empty" in str(exc_info.value)
    
    @patch('core.s3.get_s3_client')
    def test_download_image_not_found(self, mock_get_client):
        """Test that download_image raises S3DownloadError when object not found."""
        # Setup mock
        mock_client = MagicMock()
        error_response = {
            'Error': {
                'Code': 'NoSuchKey',
                'Message': 'The specified key does not exist'
            }
        }
        mock_client.get_object.side_effect = ClientError(error_response, 'GetObject')
        mock_get_client.return_value = mock_client
        
        # Execute and verify
        with pytest.raises(S3DownloadError) as exc_info:
            download_image("test/nonexistent.jpg")
        
        assert "Object not found" in str(exc_info.value)
    
    @patch('core.s3.get_s3_client')
    def test_download_image_client_error(self, mock_get_client):
        """Test that download_image raises S3DownloadError on ClientError."""
        # Setup mock
        mock_client = MagicMock()
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'Access denied'
            }
        }
        mock_client.get_object.side_effect = ClientError(error_response, 'GetObject')
        mock_get_client.return_value = mock_client
        
        # Execute and verify
        with pytest.raises(S3DownloadError) as exc_info:
            download_image("test/image.jpg")
        
        assert "Failed to download image from S3" in str(exc_info.value)
    
    @patch('core.s3.get_s3_client')
    def test_download_image_botocore_error(self, mock_get_client):
        """Test that download_image raises S3DownloadError on BotoCoreError."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.get_object.side_effect = BotoCoreError()
        mock_get_client.return_value = mock_client
        
        # Execute and verify
        with pytest.raises(S3DownloadError):
            download_image("test/image.jpg")
    
    @patch('core.s3.get_s3_client')
    def test_download_image_unexpected_error(self, mock_get_client):
        """Test that download_image raises S3DownloadError on unexpected error."""
        # Setup mock
        mock_client = MagicMock()
        mock_client.get_object.side_effect = Exception("Unexpected error")
        mock_get_client.return_value = mock_client
        
        # Execute and verify
        with pytest.raises(S3DownloadError):
            download_image("test/image.jpg")
