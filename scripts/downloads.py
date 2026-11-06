"""Fetch model files once, into ~/.barneycat/models."""

from __future__ import annotations

import shutil
import ssl
import tarfile
import urllib.request
from pathlib import Path

import certifi


def file(url: str, folder: Path, log=print) -> Path:
    target = folder / url.rsplit("/", 1)[1]
    if target.exists():
        return target
    log(f"downloading {target.name}")
    partial = target.with_name(target.name + ".partial")
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(url, context=context) as response, partial.open("wb") as handle:
        shutil.copyfileobj(response, handle, 1024 * 1024)
    partial.replace(target)
    return target


def archive(url: str, folder: Path, log=print) -> Path:
    """Download a .tar.bz2 and unpack it into a folder named after it."""
    target = folder / url.rsplit("/", 1)[1].removesuffix(".tar.bz2")
    if target.exists():
        return target
    packed = file(url, folder, log)
    log(f"unpacking {packed.name}")
    staging = folder / (target.name + ".partial")
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    with tarfile.open(packed, "r:bz2") as handle:
        handle.extractall(staging, filter="data")
    (staging / target.name).replace(target)
    staging.rmdir()
    packed.unlink()
    return target
