"""Transcription engines. Each one returns segments with word-level timestamps:

    [{"start": 0.0, "end": 2.1, "text": "...", "words": [{"word": "...", "start": 0.0, "end": 0.4}]}]

Modules load on demand, because several of them only install on some machines.
"""

from __future__ import annotations

import importlib
import platform
import sys

MODULES = {
    "parakeet-mlx": "engines.parakeet_mlx",
    "whisper-mlx": "engines.whisper_mlx",
    "whisper-faster": "engines.whisper_faster",
    "parakeet-sherpa": "engines.parakeet_sherpa",
}
NAMES = list(MODULES)


def has_cuda() -> bool:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:  # noqa: BLE001 - ctranslate2 can fail without a CUDA driver
        return False


def default_name() -> str:
    """Whisper wins on names and technical terms, and it is the only family that takes a
    vocabulary hint. Parakeet is faster, so it stays available for when speed matters more.
    """
    if sys.platform == "darwin" and platform.machine() == "arm64":
        return "whisper-mlx"
    return "whisper-faster"


def resolve(name: str):
    return importlib.import_module(MODULES[default_name() if name == "auto" else name])
