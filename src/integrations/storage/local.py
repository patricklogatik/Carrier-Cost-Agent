"""Local filesystem storage backend."""

import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import aiofiles
import aiofiles.os

from src.core.config import settings
from src.core.logging import get_logger
from src.integrations.storage.base import StorageBackend, StoredFile

logger = get_logger(__name__)


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage for development and testing."""

    def __init__(self, base_path: str | None = None) -> None:
        """Initialize local storage.

        Args:
            base_path: Base directory for storage. Defaults to settings.
        """
        self.base_path = Path(base_path or settings.storage_local_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _generate_path(self, filename: str, folder: str = "") -> str:
        """Generate a unique storage path.

        Args:
            filename: Original filename.
            folder: Optional folder.

        Returns:
            Unique path for the file.
        """
        # Generate date-based path for organization
        date_path = datetime.now().strftime("%Y/%m/%d")

        # Generate unique filename to avoid collisions
        ext = Path(filename).suffix
        unique_name = f"{uuid4().hex}{ext}"

        if folder:
            return f"{folder}/{date_path}/{unique_name}"
        return f"{date_path}/{unique_name}"

    async def upload(
        self,
        content: bytes,
        filename: str,
        folder: str = "",
        content_type: str = "application/octet-stream",
    ) -> StoredFile:
        """Upload a file to local storage.

        Args:
            content: File content as bytes.
            filename: Original filename.
            folder: Optional folder path.
            content_type: MIME type of the file.

        Returns:
            StoredFile with path and metadata.
        """
        relative_path = self._generate_path(filename, folder)
        full_path = self.base_path / relative_path

        # Create parent directories
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(content)

        logger.info(
            "File uploaded",
            path=relative_path,
            size=len(content),
        )

        return StoredFile(
            path=relative_path,
            filename=filename,
            size_bytes=len(content),
            content_type=content_type,
        )

    async def download(self, path: str) -> bytes:
        """Download a file from local storage.

        Args:
            path: Path to the file in storage.

        Returns:
            File content as bytes.

        Raises:
            FileNotFoundError: If file doesn't exist.
        """
        full_path = self.base_path / path

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

    async def delete(self, path: str) -> bool:
        """Delete a file from local storage.

        Args:
            path: Path to the file in storage.

        Returns:
            True if deleted, False if not found.
        """
        full_path = self.base_path / path

        if not full_path.exists():
            return False

        await aiofiles.os.remove(full_path)

        logger.info("File deleted", path=path)
        return True

    async def exists(self, path: str) -> bool:
        """Check if a file exists in storage.

        Args:
            path: Path to the file in storage.

        Returns:
            True if exists, False otherwise.
        """
        full_path = self.base_path / path
        return full_path.exists()

    def get_url(self, path: str) -> str:
        """Get a URL to access the file.

        For local storage, returns a file:// URL.

        Args:
            path: Path to the file in storage.

        Returns:
            URL to access the file.
        """
        full_path = self.base_path / path
        return f"file://{full_path.absolute()}"
