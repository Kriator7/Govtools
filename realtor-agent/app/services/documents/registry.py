"""Versioned document template registry. Proprietary forms are not bundled."""

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.config import PROJECT_ROOT


@dataclass
class TemplateSpec:
    name: str
    version: str
    path: Path
    metadata: dict
    field_map: dict[str, str]
    required_fields: list[str]


class TemplateRegistry:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (PROJECT_ROOT / "templates" / "documents")

    def get(self, name: str, version: str | None = None) -> TemplateSpec:
        family = self.root / name
        if not family.exists():
            raise FileNotFoundError(f"Unknown document template family: {name}")
        if version is None:
            versions = sorted(path.name for path in family.iterdir() if path.is_dir())
            if not versions:
                raise FileNotFoundError(f"No versions for template {name}")
            version = versions[-1]
        folder = family / version
        metadata = {}
        meta_path = folder / "metadata.yaml"
        if meta_path.exists():
            metadata = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        field_map = json.loads((folder / "field_map.json").read_text(encoding="utf-8"))
        pdf_path = folder / "template.pdf"
        return TemplateSpec(
            name=name,
            version=version,
            path=pdf_path,
            metadata=metadata,
            field_map=field_map,
            required_fields=list(metadata.get("required_fields") or field_map.keys()),
        )
