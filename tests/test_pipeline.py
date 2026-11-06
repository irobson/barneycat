"""End to end on a generated video, with no speech in it and a path with spaces."""

import json
import subprocess
import sys
from pathlib import Path

import media

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "barneycat.py"


def run(*args):
    return subprocess.run(["uv", "run", str(SCRIPT), *args], check=True, capture_output=True, text=True, encoding="utf-8")


def make_video(path: Path) -> None:
    subprocess.run(
        [media.ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", "color=c=red:s=320x180:d=6",
         "-f", "lavfi", "-i", "color=c=blue:s=320x180:d=6",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=12",
         "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]",
         "-map", "[v]", "-map", "2:a", "-pix_fmt", "yuv420p", str(path)],
        check=True,
    )


def test_prepare_and_pdf(tmp_path):
    folder = tmp_path / "a folder with spaces"
    folder.mkdir()
    video = folder / "TedCat 2026-01-15 at 09.09.13.mp4"
    make_video(video)

    summary = json.loads(run("prepare", str(video), "--engine", "whisper-faster", "--model", "tiny", "--language", "en", "--no-diarize").stdout)

    output = Path(summary["output"])
    assert output == folder / (video.name + ".barneycat")
    assert summary["started_at"] == "2026-01-15T09:09:13"
    assert summary["frames"] == 2
    assert (output / "frames" / "00-00-10.jpg").exists() or (output / "frames" / "00-00-05.jpg").exists()
    assert "(frame: frames/00-00-00.jpg)" in (output / "transcript.md").read_text(encoding="utf-8")
    assert not (output / ".cache" / "audio.wav").exists()

    (output / "report.md").write_text("# Test\n\n![frame](frames/00-00-00.jpg)\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n", encoding="utf-8")
    run("pdf", str(output))
    assert (output / "report.pdf").stat().st_size > 1000


def test_a_missing_file_fails_clearly(tmp_path):
    result = subprocess.run(["uv", "run", str(SCRIPT), "prepare", str(tmp_path / "nope.mp4")], capture_output=True, text=True, encoding="utf-8")
    assert result.returncode != 0
    assert "file not found" in result.stderr
