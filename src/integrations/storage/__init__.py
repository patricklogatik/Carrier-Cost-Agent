"""Storage integrations for documents."""

from src.integrations.storage.base import StorageBackend
from src.integrations.storage.local import LocalStorageBackend

__all__ = ["StorageBackend", "LocalStorageBackend"]
