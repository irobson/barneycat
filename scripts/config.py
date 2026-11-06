"""Local settings. They live outside the repository, in ~/.barneycat."""

from __future__ import annotations

import hashlib
import json
import os
import tomllib
from pathlib import Path


def home() -> Path:
    return Path(os.environ.get("BARNEYCAT_HOME", Path.home() / ".barneycat")).expanduser()


def models_dir() -> Path:
    path = home() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load() -> dict:
    path = home() / "config.toml"
    if not path.exists():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_glossary(name: str | None) -> dict:
    empty = {"vocabulary": [], "corrections": {}}
    if not name:
        return empty
    path = home() / "glossaries" / f"{name}.toml"
    if not path.exists():
        raise SystemExit(f"glossary not found: {path}")
    with path.open("rb") as handle:
        return {**empty, **tomllib.load(handle)}


def fingerprint(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:12]
