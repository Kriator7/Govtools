"""Document storage. Local filesystem for MVP; GCS for production."""

from abc import ABC, abstractmethod
from pathlib import Path

from app.config import PROJECT_ROOT, get_settings


class StorageBackend(ABC):
    @abstractmethod
    def write_bytes(self, relative_path: str, data: bytes) -> str:
        raise NotImplementedError

    @abstractmethod
    def read_bytes(self, relative_path: str) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def exists(self, relative_path: str) -> bool:
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    def __init__(self, root: Path | None = None) -> None:
        settings = get_settings()
        self.root = root or settings.storage_path
        self.root.mkdir(parents=True, exist_ok=True)

    def write_bytes(self, relative_path: str, data: bytes) -> str:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and "executed" in Path(relative_path).parts:
            raise FileExistsError("Executed documents cannot be overwritten")
        path.write_bytes(data)
        return str(path)

    def read_bytes(self, relative_path: str) -> bytes:
        return (self.root / relative_path).read_bytes()

    def exists(self, relative_path: str) -> bool:
        return (self.root / relative_path).exists()


class GcsStorageBackend(StorageBackend):
    """Cloud Storage adapter. Requires the gcp extra.

    Objects: https://cloud.google.com/storage/docs/uploading-objects
    """

    def __init__(self, bucket_name: str) -> None:
        self.bucket_name = bucket_name

    def _client(self):
        try:
            from google.cloud import storage
        except ImportError as exc:
            raise RuntimeError("Install realtor-agent[gcp] to use Cloud Storage") from exc
        return storage.Client()

    def write_bytes(self, relative_path: str, data: bytes) -> str:
        bucket = self._client().bucket(self.bucket_name)
        blob = bucket.blob(relative_path)
        if "executed" in Path(relative_path).parts and blob.exists():
            raise FileExistsError("Executed documents cannot be overwritten")
        blob.upload_from_string(data)
        return f"gs://{self.bucket_name}/{relative_path}"

    def read_bytes(self, relative_path: str) -> bytes:
        bucket = self._client().bucket(self.bucket_name)
        return bucket.blob(relative_path).download_as_bytes()

    def exists(self, relative_path: str) -> bool:
        bucket = self._client().bucket(self.bucket_name)
        return bucket.blob(relative_path).exists()


def default_storage() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend == "gcs" and settings.gcs_bucket:
        return GcsStorageBackend(settings.gcs_bucket)
    return LocalStorageBackend()
