#!/usr/bin/env python3
"""Placeholder for moving generated documents between storage prefixes."""

from app.config import get_settings


def main() -> int:
    settings = get_settings()
    print(
        {
            "storage_backend": settings.storage_backend,
            "local_storage_path": str(settings.storage_path),
            "note": "Executed documents are never overwritten.",
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
