"""Everything that touches ffmpeg."""

from __future__ import annotations

import re
import shutil
import subprocess
import wave
from datetime import datetime
from functools import cache
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000
TEDCAT_NAME = re.compile(r"TedCat (\d{4}-\d{2}-\d{2}) at (\d{2})\.(\d{2})\.(\d{2})")


@cache
def ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def inspect(path: Path) -> dict:
    """Read duration and tracks. Uses ffmpeg alone because the bundled binary has no ffprobe."""
    result = subprocess.run(
        [ffmpeg(), "-hide_banner", "-i", str(path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    text = result.stderr
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", text)
    if not match:
        raise SystemExit(f"ffmpeg could not read {path}")
    hours, minutes, seconds = match.groups()
    # Cover art shows up as a video stream on audio files, so it does not count.
    video = [line for line in text.splitlines() if "Video:" in line and "attached pic" not in line]
    return {
        "duration": int(hours) * 3600 + int(minutes) * 60 + float(seconds),
        "has_video": bool(video),
        "has_audio": "Audio:" in text,
    }


def start_time_from_name(name: str) -> datetime | None:
    match = TEDCAT_NAME.search(name)
    if not match:
        return None
    day, hours, minutes, seconds = match.groups()
    return datetime.fromisoformat(f"{day}T{hours}:{minutes}:{seconds}")


def extract_audio(source: Path, target: Path) -> None:
    partial = target.with_suffix(".partial.wav")
    subprocess.run(
        [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
         "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", str(partial)],
        check=True,
    )
    partial.replace(target)


def read_wav(path: Path) -> np.ndarray:
    """Samples as float32 in [-1, 1], the shape sherpa-onnx expects."""
    with wave.open(str(path), "rb") as handle:
        data = handle.readframes(handle.getnframes())
    return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
