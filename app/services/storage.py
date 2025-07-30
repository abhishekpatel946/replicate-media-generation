"""
File storage service for media files.
Handles local filesystem storage with S3-compatible interface design.
"""

import os
import json
import aiofiles
from pathlib import Path
from uuid import UUID
from typing import Dict, Any

from app.core.config import settings


class StorageError(Exception):
    """Custom exception for storage operations."""

    pass


class LocalFileStorage:
    """
    Local filesystem storage implementation.
    Designed to be easily replaceable with S3-compatible storage.
    """

    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path or settings.storage_path)
        self.metadata_path = self.base_path.parent / "metadata"
        self.base_url = settings.storage_base_url
        self._ensure_directories_exist()

    def _ensure_directories_exist(self):
        """Create storage directories if they don't exist."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.metadata_path.mkdir(parents=True, exist_ok=True)

    def _generate_file_path(
        self, job_id: UUID, extension: str = "png"
    ) -> Path:
        """Generate file path for a job."""
        filename = f"{job_id}.{extension}"
        return self.base_path / filename

    def _generate_metadata_path(self, job_id: UUID) -> Path:
        """Generate metadata file path for a job."""
        filename = f"{job_id}.json"
        return self.metadata_path / filename

    def _generate_file_url(self, job_id: UUID, extension: str = "png") -> str:
        """Generate public URL for a file."""
        filename = f"{job_id}.{extension}"
        return f"{self.base_url}/{filename}"

    async def save_file(
        self, job_id: UUID, file_data: bytes, extension: str = "png"
    ) -> tuple[str, str]:
        """
        Save file data to storage.

        Args:
            job_id: Unique job identifier
            file_data: File content as bytes
            extension: File extension without dot

        Returns:
            Tuple of (file_path, file_url)

        Raises:
            StorageError: If save operation fails
        """
        try:
            file_path = self._generate_file_path(job_id, extension)
            file_url = self._generate_file_url(job_id, extension)

            async with aiofiles.open(file_path, "wb") as f:
                await f.write(file_data)

            return str(file_path), file_url

        except Exception as e:
            raise StorageError(f"Failed to save file for job {job_id}: {e}")

    async def save_metadata(
        self, job_id: UUID, metadata: Dict[str, Any]
    ) -> str:
        """
        Save generation metadata to storage.

        Args:
            job_id: Unique job identifier
            metadata: Generation parameters and metadata

        Returns:
            Path to saved metadata file

        Raises:
            StorageError: If save operation fails
        """
        try:
            metadata_path = self._generate_metadata_path(job_id)

            async with aiofiles.open(metadata_path, "w") as f:
                await f.write(json.dumps(metadata, indent=2))

            return str(metadata_path)

        except Exception as e:
            raise StorageError(
                f"Failed to save metadata for job {job_id}: {e}"
            )

    async def get_file(
        self, job_id: UUID, extension: str = "png"
    ) -> bytes:
        """
        Retrieve file data from storage.

        Args:
            job_id: Unique job identifier
            extension: File extension without dot

        Returns:
            File content as bytes

        Raises:
            StorageError: If file doesn't exist or read fails
        """
        try:
            file_path = self._generate_file_path(job_id, extension)

            if not file_path.exists():
                raise StorageError(f"File not found for job {job_id}")

            async with aiofiles.open(file_path, "rb") as f:
                return await f.read()

        except Exception as e:
            raise StorageError(f"Failed to read file for job {job_id}: {e}")

    async def get_metadata(self, job_id: UUID) -> Dict[str, Any]:
        """
        Retrieve generation metadata from storage.

        Args:
            job_id: Unique job identifier

        Returns:
            Generation metadata as dictionary

        Raises:
            StorageError: If metadata file doesn't exist or read fails
        """
        try:
            metadata_path = self._generate_metadata_path(job_id)

            if not metadata_path.exists():
                raise StorageError(f"Metadata not found for job {job_id}")

            async with aiofiles.open(metadata_path, "r") as f:
                content = await f.read()
                return json.loads(content)

        except Exception as e:
            raise StorageError(
                f"Failed to read metadata for job {job_id}: {e}"
            )

    async def delete_file(
        self, job_id: UUID, extension: str = "png"
    ) -> bool:
        """
        Delete file from storage.

        Args:
            job_id: Unique job identifier
            extension: File extension without dot

        Returns:
            True if file was deleted, False if it didn't exist

        Raises:
            StorageError: If delete operation fails
        """
        try:
            file_path = self._generate_file_path(job_id, extension)

            if file_path.exists():
                os.remove(file_path)
                return True

            return False

        except Exception as e:
            raise StorageError(f"Failed to delete file for job {job_id}: {e}")

    async def delete_metadata(self, job_id: UUID) -> bool:
        """
        Delete metadata file from storage.

        Args:
            job_id: Unique job identifier

        Returns:
            True if metadata was deleted, False if it didn't exist

        Raises:
            StorageError: If delete operation fails
        """
        try:
            metadata_path = self._generate_metadata_path(job_id)

            if metadata_path.exists():
                os.remove(metadata_path)
                return True

            return False

        except Exception as e:
            raise StorageError(
                f"Failed to delete metadata for job {job_id}: {e}"
            )

    def get_file_url(self, job_id: UUID, extension: str = "png") -> str:
        """Get public URL for a file."""
        return self._generate_file_url(job_id, extension)

    def get_file_path(self, job_id: UUID, extension: str = "png") -> str:
        """Get filesystem path for a file."""
        return str(self._generate_file_path(job_id, extension))

    def get_metadata_path(self, job_id: UUID) -> str:
        """Get filesystem path for metadata file."""
        return str(self._generate_metadata_path(job_id))


# TODO: For production, implement S3-compatible storage
class S3FileStorage:
    """
    S3-compatible storage implementation (placeholder).

    This would be implemented for production deployment with:
    - AWS S3, MinIO, or other S3-compatible storage
    - Proper authentication and bucket management
    - Presigned URLs for secure access
    - Lifecycle policies for cleanup
    """

    pass


# Global storage instance
# In production, this would be configurable via environment variables
storage_service = LocalFileStorage()
