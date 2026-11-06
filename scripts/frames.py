"""Pick the frames worth looking at.

Sampling and comparing small grayscale copies catches what matters in a screen share:
a new slide can change too few pixels for ffmpeg's scene score. The catch is the
webcams, which change all the time and mean nothing. So pixels that keep changing
around a given moment are ignored at that moment, whatever part of the screen they
are in, and the layout of the call can change freely during the meeting.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

import media

SAMPLE_EVERY = 5.0
THUMB_WIDTH, THUMB_HEIGHT = 160, 90
PIXEL_DELTA = 20
CHANGED_SHARE = 0.02
MIN_GAP = 15.0
BIG_CHANGE = 0.3
MAX_GAP = 120.0
MAX_FRAMES = 60
RESTLESS_WINDOW = 12
RESTLESS_SHARE = 0.35
MIN_SAMPLES_FOR_MASK = 24
OUTPUT_WIDTH = 1600


def sample(source: Path) -> np.ndarray:
    size = THUMB_WIDTH * THUMB_HEIGHT
    command = [
        media.ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", str(source), "-an",
        "-vf", f"fps=1/{SAMPLE_EVERY},scale={THUMB_WIDTH}:{THUMB_HEIGHT},format=gray",
        "-f", "rawvideo", "-",
    ]
    raw = subprocess.run(command, check=True, capture_output=True).stdout
    return np.frombuffer(raw[: len(raw) // size * size], dtype=np.uint8).reshape(-1, size)


def calm_masks(thumbs: np.ndarray) -> np.ndarray:
    """For each sample, the pixels that were not restless in the samples around it."""
    if len(thumbs) < MIN_SAMPLES_FOR_MASK:
        return np.ones(thumbs.shape, dtype=bool)
    moved = np.abs(np.diff(thumbs.astype(np.int16), axis=0)) > PIXEL_DELTA
    totals = np.vstack([np.zeros((1, moved.shape[1]), dtype=np.int32), np.cumsum(moved, axis=0, dtype=np.int32)])
    masks = np.empty(thumbs.shape, dtype=bool)
    for index in range(len(thumbs)):
        low = max(index - RESTLESS_WINDOW, 0)
        high = min(index + RESTLESS_WINDOW, len(moved))
        masks[index] = (totals[high] - totals[low]) / max(high - low, 1) < RESTLESS_SHARE
    return masks


def select(thumbs: np.ndarray, max_frames: int) -> list[dict]:
    """Keep frames that differ from the last kept one, and at least one per MAX_GAP."""
    if len(thumbs) == 0:
        return []
    masks = calm_masks(thumbs)
    kept = [{"time": 0.0, "reason": "start", "change": 1.0}]
    reference = thumbs[0].astype(np.int16)
    for index in range(1, len(thumbs)):
        current = thumbs[index].astype(np.int16)
        calm = masks[index]
        change = float(np.mean(np.abs(current - reference)[calm] > PIXEL_DELTA)) if calm.any() else 0.0
        moment = index * SAMPLE_EVERY
        since_last = moment - kept[-1]["time"]
        if change >= BIG_CHANGE or (change >= CHANGED_SHARE and since_last >= MIN_GAP):
            reason = "change"
        elif since_last >= MAX_GAP:
            reason = "interval"
        else:
            continue
        kept.append({"time": moment, "reason": reason, "change": round(change, 4)})
        reference = current
    if len(kept) > max_frames:
        strongest = sorted(kept, key=lambda frame: frame["change"], reverse=True)[:max_frames]
        kept = sorted(strongest, key=lambda frame: frame["time"])
    return kept


def label(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 3600:02d}-{total % 3600 // 60:02d}-{total % 60:02d}"


def extract(source: Path, target: Path, duration: float, max_frames: int = MAX_FRAMES) -> list[dict]:
    picked = select(sample(source), max_frames)
    for frame in picked:
        # A second later than the sample, so a slide caught mid-transition has settled.
        moment = min(frame["time"] + 1.0, max(duration - 0.5, 0.0))
        frame["file"] = f"frames/{label(frame['time'])}.jpg"
        subprocess.run(
            [media.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{moment:.2f}",
             "-i", str(source), "-frames:v", "1", "-vf", f"scale='min({OUTPUT_WIDTH},iw)':-2",
             "-q:v", "3", str(target.parent / frame["file"])],
            check=True,
        )
    return picked
