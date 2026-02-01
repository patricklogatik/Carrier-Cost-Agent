"""Base storage backend interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StoredFile:
    """Information about a stored file."""

    path: str
    filename: str
    size_bytes: int
    content_type: str


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def upload(
        self,
        content: bytes,
        filename: str,
        folder: str = "",
        content_type: str = "application/octet-stream",
    ) -> StoredFile:
        """Upload a file to storage.

        Args:
            content: File content as bytes.
            filename: Original filename.
            folder: Optional folder path.
            content_type: MIME type of the file.

        Returns:
            StoredFile with path and metadata.
        """
        pass

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Download a file from storage.

        Args:
            path: Path to the file in storage.

        Returns:
            File content as bytes.
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete a file from storage.

        Args:
            path: Path to the file in storage.

        Returns:
            True if deleted, False if not found.
        """
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if a file exists in storage.

        Args:
            path: Path to the file in storage.

        Returns:
            True if exists, False otherwise.
        """
        pass

    @abstractmethod
    def get_url(self, path: str) -> str:
        """Get a URL to access the file.

        Args:
            path: Path to the file in storage.

        Returns:
            URL to access the file.
        """
        pass
