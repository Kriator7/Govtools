"""Secret backends. Never persist raw credentials in PostgreSQL."""

from abc import ABC, abstractmethod
import os


class SecretBackend(ABC):
    @abstractmethod
    def get(self, name: str) -> str | None:
        raise NotImplementedError


class EnvSecretBackend(SecretBackend):
    def get(self, name: str) -> str | None:
        return os.environ.get(name)


class GcpSecretBackend(SecretBackend):
    """Google Secret Manager adapter. Requires the gcp extra.

    Access API: https://cloud.google.com/secret-manager/docs/access-secret-version
    """

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id

    def get(self, name: str) -> str | None:
        try:
            from google.cloud import secretmanager
        except ImportError as exc:
            raise RuntimeError("Install realtor-agent[gcp] to use Secret Manager") from exc
        client = secretmanager.SecretManagerServiceClient()
        path = f"projects/{self.project_id}/secrets/{name}/versions/latest"
        response = client.access_secret_version(request={"name": path})
        return response.payload.data.decode("utf-8")
