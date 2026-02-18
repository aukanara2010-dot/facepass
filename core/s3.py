"""
S3 storage client module for Beget S3 integration.

This module provides functions for interacting with Beget S3 storage,
including uploading and downloading images with proper error handling.
"""

import logging
from typing import Optional, List

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, BotoCoreError

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class S3Error(Exception):
    """Base exception for S3 operations."""
    pass


class S3UploadError(S3Error):
    """Exception raised when S3 upload fails."""
    pass


class S3DownloadError(S3Error):
    """Exception raised when S3 download fails."""
    pass


class S3ConnectionError(S3Error):
    """Exception raised when S3 connection fails."""
    pass


def get_s3_client():
    """
    Create and return S3 client for Beget storage.
    
    This function creates a boto3 S3 client configured for Beget S3 storage
    with the appropriate endpoint, credentials, and region settings.
    
    Returns:
        boto3.client: Configured S3 client
        
    Raises:
        S3ConnectionError: If client creation fails
        
    Example:
        s3_client = get_s3_client()
        s3_client.list_buckets()
    """
    try:
        return boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=Config(
                signature_version='s3v4',
                s3={
                    'payload_signing_enabled': False,  # Disable Content-SHA256 to fix XAmzContentSHA256Mismatch
                    'addressing_style': 'path'  # Use path-style addressing for compatibility
                }
            )
        )
    except Exception as e:
        logger.error(f"Failed to create S3 client: {e}")
        raise S3ConnectionError(f"Failed to create S3 client: {e}") from e


def upload_image(file_data: bytes, object_name: str, content_type: str = 'image/jpeg') -> str:
    """
    Upload image to S3 bucket.
    
    This function uploads binary image data to the configured S3 bucket
    and returns the URL of the uploaded object.
    
    Args:
        file_data: Image binary data to upload
        object_name: Object key in S3 bucket (e.g., "faces/user123/image.jpg")
        content_type: MIME type of the image (default: 'image/jpeg')
    
    Returns:
        str: URL of uploaded object
        
    Raises:
        S3UploadError: If upload fails
        ValueError: If file_data is empty or object_name is invalid
        
    Example:
        with open("face.jpg", "rb") as f:
            image_data = f.read()
        url = upload_image(image_data, "faces/user123/face.jpg")
        print(f"Uploaded to: {url}")
    """
    if not file_data:
        raise ValueError("file_data cannot be empty")
    
    if not object_name or not object_name.strip():
        raise ValueError("object_name cannot be empty")
    
    try:
        s3_client = get_s3_client()
        s3_client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=object_name,
            Body=file_data,
            ContentType=content_type
        )
        
        # Construct the URL for the uploaded object
        url = f"{settings.S3_ENDPOINT}/{settings.S3_BUCKET}/{object_name}"
        logger.info(f"Successfully uploaded image to S3: {object_name}")
        return url
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"S3 ClientError during upload: {error_code} - {error_message}")
        raise S3UploadError(f"Failed to upload image to S3: {error_message}") from e
        
    except BotoCoreError as e:
        logger.error(f"BotoCoreError during upload: {e}")
        raise S3UploadError(f"Failed to upload image to S3: {e}") from e
        
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}")
        raise S3UploadError(f"Failed to upload image to S3: {e}") from e


def download_image(object_name: str) -> bytes:
    """
    Download image from S3 bucket.
    
    This function downloads an image from the configured S3 bucket
    and returns its binary data.
    
    Args:
        object_name: Object key in S3 bucket (e.g., "faces/user123/image.jpg")
    
    Returns:
        bytes: Image binary data
        
    Raises:
        S3DownloadError: If download fails
        ValueError: If object_name is invalid
        
    Example:
        image_data = download_image("faces/user123/face.jpg")
        with open("downloaded_face.jpg", "wb") as f:
            f.write(image_data)
    """
    if not object_name or not object_name.strip():
        raise ValueError("object_name cannot be empty")
    
    try:
        s3_client = get_s3_client()
        response = s3_client.get_object(
            Bucket=settings.S3_BUCKET,
            Key=object_name
        )
        
        image_data = response['Body'].read()
        logger.info(f"Successfully downloaded image from S3: {object_name}")
        return image_data
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        
        if error_code == 'NoSuchKey':
            logger.error(f"Object not found in S3: {object_name}")
            raise S3DownloadError(f"Object not found: {object_name}") from e
        
        logger.error(f"S3 ClientError during download: {error_code} - {error_message}")
        raise S3DownloadError(f"Failed to download image from S3: {error_message}") from e
        
    except BotoCoreError as e:
        logger.error(f"BotoCoreError during download: {e}")
        raise S3DownloadError(f"Failed to download image from S3: {e}") from e
        
    except Exception as e:
        logger.error(f"Unexpected error during download: {e}")
        raise S3DownloadError(f"Failed to download image from S3: {e}") from e


def list_s3_objects(prefix: str) -> List[str]:
    """
    List all objects in S3 bucket with given prefix.
    
    This function lists all objects in the configured S3 bucket
    that match the given prefix.
    
    Args:
        prefix: Prefix to filter objects (e.g., "events/1/previews/")
    
    Returns:
        List[str]: List of object keys
        
    Raises:
        S3DownloadError: If listing fails
        ValueError: If prefix is invalid
        
    Example:
        objects = list_s3_objects("events/1/previews/")
        print(f"Found {len(objects)} objects")
    """
    if not prefix or not prefix.strip():
        raise ValueError("prefix cannot be empty")
    
    try:
        s3_client = get_s3_client()
        
        # List objects with pagination
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=settings.S3_BUCKET, Prefix=prefix)
        
        objects = []
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects.append(obj['Key'])
        
        logger.info(f"Found {len(objects)} objects with prefix: {prefix}")
        return objects
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"S3 ClientError during listing: {error_code} - {error_message}")
        raise S3DownloadError(f"Failed to list S3 objects: {error_message}") from e
        
    except BotoCoreError as e:
        logger.error(f"BotoCoreError during listing: {e}")
        raise S3DownloadError(f"Failed to list S3 objects: {e}") from e
        
    except Exception as e:
        logger.error(f"Unexpected error during listing: {e}")
        raise S3DownloadError(f"Failed to list S3 objects: {e}") from e
