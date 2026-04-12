#!/usr/bin/env python3
"""Validate config JSON files for standardized _meta schema.

Checks every JSON file in config/ for a top-level _meta object with required keys.
Exits non-zero if validation fails.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_META_SCHEMA = {
    "version": str,
    "owner": str,
    "last_updated": str,
    "purpose": str,
    "examples": list,
    "notes": list,
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_meta(meta: object, file_path: Path) -> list[str]:
    errors: list[str] = []

    if not isinstance(meta, dict):
        return [f"{file_path.name}: _meta must be an object"]

    for key, expected_type in REQUIRED_META_SCHEMA.items():
        if key not in meta:
            errors.append(f"{file_path.name}: _meta missing required key '{key}'")
            continue

        value = meta[key]
        if not isinstance(value, expected_type):
            errors.append(
                f"{file_path.name}: _meta.{key} must be {expected_type.__name__}"
            )
            continue

        if expected_type is str and not _is_non_empty_string(value):
            errors.append(f"{file_path.name}: _meta.{key} cannot be empty")

        if key == "last_updated" and isinstance(value, str) and not DATE_RE.match(value):
            errors.append(
                f"{file_path.name}: _meta.last_updated must be YYYY-MM-DD"
            )

        if expected_type is list:
            if not value:
                errors.append(f"{file_path.name}: _meta.{key} cannot be empty")
            elif not all(_is_non_empty_string(item) for item in value):
                errors.append(
                    f"{file_path.name}: _meta.{key} must contain only non-empty strings"
                )

    return errors


def validate_config_dir(config_dir: Path) -> tuple[list[str], int]:
    errors: list[str] = []
    inspected = 0

    if not config_dir.exists() or not config_dir.is_dir():
        return [f"Config directory not found: {config_dir}"], 0

    for json_file in sorted(config_dir.glob("*.json")):
        inspected += 1
        try:
            payload = json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{json_file.name}: invalid JSON ({exc})")
            continue

        if not isinstance(payload, dict):
            errors.append(f"{json_file.name}: top-level JSON must be an object")
            continue

        meta = payload.get("_meta")
        errors.extend(_validate_meta(meta, json_file))

    return errors, inspected


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate config _meta schema")
    parser.add_argument(
        "--config-dir",
        default="config",
        help="Path to config directory (default: config)",
    )
    args = parser.parse_args()

    config_dir = Path(args.config_dir).resolve()
    errors, inspected = validate_config_dir(config_dir)

    if inspected == 0 and not errors:
        print("No JSON config files found.")
        return 1

    if errors:
        print("Config meta validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Config meta validation passed for {inspected} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
