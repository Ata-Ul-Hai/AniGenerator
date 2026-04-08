"""Abstraction layer for artifact storage (Local vs GCS)."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path

from google.cloud import storage

logger = logging.getLogger(__name__)


class StorageProvider(ABC):
    """Base interface for all storage backends."""

    @abstractmethod
    def upload_file(self, local_path: str | Path, remote_rel_path: str) -> str:
        """Upload a file and return its public or relative access URL."""
        pass

    @abstractmethod
    def get_url(self, remote_rel_path: str) -> str:
        """Return the accessible URL for a given relative path."""
        pass


class LocalStorageProvider(StorageProvider):
    """Provider for local filesystem storage (Development)."""

    def __init__(self, base_dir: Path, public_url_prefix: str = "/artifacts"):
        self.base_dir = base_dir
        self.public_url_prefix = public_url_prefix

    def upload_file(self, local_path: str | Path, remote_rel_path: str) -> str:
        # For local, we assume files are already written to the renderer/public dir
        # or we could explicitly copy them if needed.
        # Here we just return the relative path prefix.
        return self.get_url(remote_rel_path)

    def get_url(self, remote_rel_path: str) -> str:
        # Strip 'public/' if it exists in the path for the URL
        if remote_rel_path.startswith("public/"):
            remote_rel_path = remote_rel_path[len("public/") :]
        return f"{self.public_url_prefix}/{remote_rel_path.lstrip('/')}"


class GcsStorageProvider(StorageProvider):
    """Provider for Google Cloud Storage (Production)."""

    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def upload_file(self, local_path: str | Path, remote_rel_path: str) -> str:
        """Upload to GCS and return the GCS-style artifact path."""
        blob = self.bucket.blob(remote_rel_path)
        blob.upload_from_filename(str(local_path))
        logger.info("Uploaded %s to gs://%s/%s", local_path, self.bucket_name, remote_rel_path)
        return self.get_url(remote_rel_path)

    def get_url(self, remote_rel_path: str) -> str:
        # In a real setup, we might return a Signed URL or a CDN URL.
        # For now, we return 'artifacts/path' which the backend will resolve
        # or the frontend will use to build the URL.
        return f"artifacts/{remote_rel_path.lstrip('/')}"


def get_storage_provider(settings: Any) -> StorageProvider:
    """Factory to return the correct provider based on settings."""
    if settings.app_env.lower() == "production" and settings.gcs_bucket_name:
        logger.info("Using GCS Storage Provider (bucket: %s)", settings.gcs_bucket_name)
        return GcsStorageProvider(settings.gcs_bucket_name)
    
    logger.info("Using Local Storage Provider")
    # For local, 'base_dir' is typically '../renderer/public'
    renderer_root = Path(__file__).resolve().parent.parent.parent / "renderer"
    return LocalStorageProvider(renderer_root / "public")
