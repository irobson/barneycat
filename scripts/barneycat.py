#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "certifi",
#   "faster-whisper>=1.2",
#   "imageio-ffmpeg>=0.6",
#   "markdown>=3.5",
#   "mlx-whisper>=0.4.2; sys_platform == 'darwin' and platform_machine == 'arm64'",
#   "numpy",
#   "parakeet-mlx>=0.5; sys_platform == 'darwin' and platform_machine == 'arm64'",
#   "pymupdf",
#   "sherpa-onnx>=1.12",
# ]
# ///
"""BarneyCat: turn a meeting recording into material an agent can read.

`prepare` extracts the audio, transcribes it, separates the speakers and picks the
frames worth looking at. It interprets nothing: the agent that called it writes the
report. `pdf` renders that report once it exists.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

import config
import engines
import frames as frames_step
import media
import pdf as pdf_step
import speakers
import transcript as transcript_step


def log(message: str) -> None:
    print(f"[barneycat] {message}", file=sys.stderr, flush=True)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def prepare(args: argparse.Namespace) -> dict:
    source = Path(args.path).expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"file not found: {source}")

    out = Path(args.out).expanduser().resolve() if args.out else source.with_name(source.name + ".barneycat")
    cache = out / ".cache"
    cache.mkdir(parents=True, exist_ok=True)

    settings = config.load()
    language = args.language or settings.get("language")
    glossary = config.load_glossary(args.glossary)
    warnings: list[str] = []

    info = media.inspect(source)
    if not info["has_audio"]:
        raise SystemExit(f"no audio track in {source}")
    started_at = media.start_time_from_name(source.name)
    log(f"{source.name}: {info['duration'] / 60:.1f} min, video={info['has_video']}, start={started_at}")

    audio = cache / "audio.wav"

    def ensure_audio() -> Path:
        if not audio.exists():
            log("extracting audio")
            media.extract_audio(source, audio)
        return audio

    engine = engines.resolve(args.engine)
    model = args.model or engine.default_model
    key = config.fingerprint(engine.name, model, language, glossary["vocabulary"])
    raw_path = cache / f"transcript-{key}.json"
    if raw_path.exists() and not args.force:
        log("transcript found in cache")
        segments = load_json(raw_path)
    else:
        log(f"transcribing with {engine.name} ({model}); the first run downloads the model")
        began = time.monotonic()
        segments = engine.transcribe(ensure_audio(), model=model, language=language, vocabulary=glossary["vocabulary"], log=log)
        log(f"transcribed in {time.monotonic() - began:.0f}s")
        save_json(raw_path, segments)

    turns: list[dict] = []
    if not args.no_diarize:
        turns_path = cache / "speakers.json"
        if turns_path.exists() and not args.force:
            turns = load_json(turns_path)
        else:
            log("separating speakers")
            began = time.monotonic()
            try:
                turns = speakers.diarize(ensure_audio(), log=log)
                save_json(turns_path, turns)
                log(f"found {len({t['speaker'] for t in turns})} speakers in {time.monotonic() - began:.0f}s")
            except Exception as error:  # noqa: BLE001 - a transcript without speakers is still useful
                warnings.append(f"speaker separation failed: {error}")
                log(warnings[-1])

    picked: list[dict] = []
    if info["has_video"] and not args.no_frames:
        frames_dir = out / "frames"
        index = frames_dir / "index.json"
        if index.exists() and not args.force:
            picked = load_json(index)
        else:
            log("picking frames")
            shutil.rmtree(frames_dir, ignore_errors=True)
            frames_dir.mkdir(parents=True)
            picked = frames_step.extract(source, frames_dir, info["duration"], max_frames=args.max_frames)
            save_json(index, picked)
            log(f"kept {len(picked)} frames")

    corrected = transcript_step.apply_corrections(segments, glossary["corrections"])
    utterances = transcript_step.build_utterances(corrected, turns)
    save_json(out / "transcript.json", {"segments": corrected, "utterances": utterances})
    (out / "transcript.md").write_text(
        transcript_step.render(utterances, picked, started_at), encoding="utf-8"
    )

    summary = {
        "source": str(source),
        "output": str(out),
        "duration_seconds": info["duration"],
        "started_at": started_at.isoformat() if started_at else None,
        "engine": engine.name,
        "model": model,
        "language": language,
        "glossary": args.glossary,
        "speakers": len({u["speaker"] for u in utterances if u["speaker"]}),
        "frames": len(picked),
        "user": {"name": settings.get("name"), "aliases": settings.get("aliases", [])},
        "reports_dir": settings.get("reports_dir"),
        "warnings": warnings,
    }
    save_json(out / "info.json", summary)
    audio.unlink(missing_ok=True)
    return summary


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(prog="barneycat", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("prepare", help="transcribe a recording and pick its frames")
    run.add_argument("path")
    run.add_argument("--language", help="language code such as pt or en; autodetected when omitted")
    run.add_argument("--glossary", help="name of a glossary in ~/.barneycat/glossaries")
    run.add_argument("--engine", default="auto", choices=["auto", *engines.NAMES])
    run.add_argument("--model", help="override the engine's default model")
    run.add_argument("--out", help="output folder; defaults to <recording>.barneycat next to the file")
    run.add_argument("--max-frames", type=int, default=frames_step.MAX_FRAMES)
    run.add_argument("--no-diarize", action="store_true")
    run.add_argument("--no-frames", action="store_true")
    run.add_argument("--force", action="store_true", help="ignore cached results")

    render = commands.add_parser("pdf", help="render report.md to report.pdf")
    render.add_argument("folder")

    args = parser.parse_args()
    if args.command == "prepare":
        print(json.dumps(prepare(args), ensure_ascii=False, indent=2))
    else:
        print(pdf_step.render(Path(args.folder).expanduser().resolve()))


if __name__ == "__main__":
    main()
