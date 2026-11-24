"""Credential file reader. Values stay out of tool results and logs."""

from __future__ import annotations

import os
from pathlib import Path


DEFAULT_PATH = Path.home() / ".config" / "jarvis" / "credentials.env"


class CredentialStore:
    def __init__(self, values: dict[str, str], path: Path | None):
        self._values = values
        self.path = path

    @classmethod
    def load(cls, path: str | Path | None = None) -> "CredentialStore":
        raw = path or os.environ.get("JARVIS_CREDENTIALS_FILE") or DEFAULT_PATH
        file_path = Path(raw).expanduser()
        values: dict[str, str] = {}
        if file_path.is_file():
            for line in file_path.read_text(encoding="utf-8").splitlines():
                text = line.strip()
                if not text or text.startswith("#") or "=" not in text:
                    continue
                key, value = text.split("=", 1)
                values[key.strip()] = value
        return cls(values, file_path if file_path.is_file() else None)

    def get(self, name: str) -> str | None:
        value = self._values.get(name)
        if value is None or value == "":
            return None
        return value

    def present(self, name: str) -> bool:
        return self.get(name) is not None

    def public_view(self) -> dict[str, bool]:
        return {key: bool(value) for key, value in self._values.items()}

    def write_key(self, name: str, value: str) -> None:
        target = Path(
            os.environ.get("JARVIS_CREDENTIALS_FILE") or (self.path or DEFAULT_PATH)
        ).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        found = False
        if target.is_file():
            for line in target.read_text(encoding="utf-8").splitlines():
                if line.startswith(name + "="):
                    lines.append(f"{name}={value}")
                    found = True
                else:
                    lines.append(line)
        if not found:
            lines.append(f"{name}={value}")
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        target.chmod(0o600)
        self._values[name] = value
        self.path = target

    def redact(self, text: str) -> str:
        redacted = text
        for value in self._values.values():
            if value and len(value) >= 8:
                redacted = redacted.replace(value, "[redacted]")
        return redacted
