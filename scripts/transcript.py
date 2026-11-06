"""Merge words and speakers into what the agent reads."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

MAX_UTTERANCE = 30.0
PAUSE = 2.0
SENTENCE_END = (".", "?", "!", "…")


def apply_corrections(segments: list[dict], corrections: dict[str, str]) -> list[dict]:
    if not corrections:
        return segments
    rules = [(re.compile(rf"\b{re.escape(wrong)}\b", re.IGNORECASE), right) for wrong, right in corrections.items()]

    def fix(text: str) -> str:
        for pattern, right in rules:
            text = pattern.sub(right, text)
        return text

    fixed = []
    for segment in segments:
        words = [{**word, "word": fix(word["word"])} for word in segment.get("words", [])]
        fixed.append({**segment, "text": fix(segment["text"]), "words": words})
    return fixed


def speaker_at(moment: float, turns: list[dict]) -> int | None:
    """The turn covering this moment, or the nearest one within a second."""
    nearest, distance = None, 1.0
    for turn in turns:
        if turn["start"] <= moment <= turn["end"]:
            return turn["speaker"]
        gap = min(abs(moment - turn["start"]), abs(moment - turn["end"]))
        if gap < distance:
            nearest, distance = turn["speaker"], gap
    return nearest


def build_utterances(segments: list[dict], turns: list[dict]) -> list[dict]:
    """Group words into lines that belong to one speaker. Labels follow order of appearance."""
    words = []
    for segment in segments:
        words.extend(segment.get("words") or [{"word": segment["text"], "start": segment["start"], "end": segment["end"]}])

    labels: dict[int, str] = {}
    utterances: list[dict] = []
    current_speaker = None
    for word in words:
        found = speaker_at((word["start"] + word["end"]) / 2, turns) if turns else None
        current_speaker = found if found is not None else current_speaker
        name = None
        if current_speaker is not None:
            name = labels.setdefault(current_speaker, f"Speaker {len(labels) + 1}")

        last = utterances[-1] if utterances else None
        fresh = (
            last is None
            or last["speaker"] != name
            or word["start"] - last["end"] >= PAUSE
            or (last["end"] - last["start"] >= MAX_UTTERANCE and last["text"].endswith(SENTENCE_END))
        )
        if fresh:
            utterances.append({"start": word["start"], "end": word["end"], "speaker": name, "text": word["word"].strip()})
        else:
            last["end"] = word["end"]
            last["text"] = f"{last['text']} {word['word'].strip()}"
    return utterances


def clock(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"


def stamp(seconds: float, started_at: datetime | None) -> str:
    if started_at is None:
        return clock(seconds)
    return f"{clock(seconds)} | {(started_at + timedelta(seconds=seconds)).strftime('%H:%M:%S')}"


def render(utterances: list[dict], frames: list[dict], started_at: datetime | None) -> str:
    """One line per utterance, with frames placed where they happened."""
    header = ["# Transcript", ""]
    if started_at:
        header += [f"Recording started at {started_at.isoformat(sep=' ')}. Stamps read: position in the file | real time.", ""]
    else:
        header += ["Stamps are positions in the file. The real time is unknown.", ""]

    lines = []
    pending = list(frames)
    for utterance in utterances:
        while pending and pending[0]["time"] <= utterance["start"]:
            frame = pending.pop(0)
            lines.append(f"[{stamp(frame['time'], started_at)}] (frame: {frame['file']})")
        who = f"{utterance['speaker']}: " if utterance["speaker"] else ""
        lines.append(f"[{stamp(utterance['start'], started_at)}] {who}{utterance['text']}")
    lines += [f"[{stamp(frame['time'], started_at)}] (frame: {frame['file']})" for frame in pending]
    return "\n".join(header + lines) + "\n"
