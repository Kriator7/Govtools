"""Small JSON-schema subset used before any tool runs."""

from __future__ import annotations

from typing import Any


class ValidationError(ValueError):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def validate(schema: dict[str, Any], value: Any, path: str = "$") -> None:
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            raise ValidationError(f"{path} must be an object")
        allowed = set(schema.get("properties") or {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - allowed)
            if extra:
                raise ValidationError(f"{path} has unknown arguments: {', '.join(extra)}")
        for name in schema.get("required") or []:
            if name not in value:
                raise ValidationError(f"{path}.{name} is required")
        for name, child in (schema.get("properties") or {}).items():
            if name in value:
                validate(child, value[name], f"{path}.{name}")
        return
    if expected == "string":
        if not isinstance(value, str):
            raise ValidationError(f"{path} must be a string")
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise ValidationError(f"{path} is too short")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ValidationError(f"{path} is too long")
        if "enum" in schema and value not in schema["enum"]:
            raise ValidationError(f"{path} must be one of {schema['enum']}")
        return
    if expected == "boolean":
        if not isinstance(value, bool):
            raise ValidationError(f"{path} must be a boolean")
        return
    if expected == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValidationError(f"{path} must be an integer")
        return
    if expected == "array":
        if not isinstance(value, list):
            raise ValidationError(f"{path} must be an array")
        item = schema.get("items")
        if item:
            for index, child in enumerate(value):
                validate(item, child, f"{path}[{index}]")
        return
    raise ValidationError(f"unsupported schema at {path}")
