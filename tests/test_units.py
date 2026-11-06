from datetime import datetime
from types import SimpleNamespace

import numpy as np

import frames
import media
import transcript
from engines import parakeet_mlx, parakeet_sherpa


def test_start_time_comes_from_a_tedcat_name():
    assert media.start_time_from_name("TedCat 2026-01-15 at 09.09.13.mp4") == datetime(2026, 1, 15, 9, 9, 13)
    assert media.start_time_from_name("TedCat 2026-01-15 at 09.09.13 (2).mp4") == datetime(2026, 1, 15, 9, 9, 13)


def test_other_names_have_no_start_time():
    assert media.start_time_from_name("kickoff.mp4") is None


def test_corrections_apply_to_text_and_words():
    segments = [{"start": 0, "end": 1, "text": "the a cme team", "words": [{"word": "cme", "start": 0, "end": 1}]}]
    fixed = transcript.apply_corrections(segments, {"a cme": "Acme", "cme": "CME"})
    assert fixed[0]["text"] == "the Acme team"
    assert fixed[0]["words"][0]["word"] == "CME"


def words(*items):
    return [{"start": start, "end": end, "text": word, "words": [{"word": word, "start": start, "end": end}]} for word, start, end in items]


def test_utterances_follow_the_speakers_in_order_of_appearance():
    segments = words(("hello", 0.0, 0.5), ("there", 0.6, 1.0), ("hi", 1.2, 1.5))
    turns = [{"start": 0.0, "end": 1.1, "speaker": 7}, {"start": 1.1, "end": 2.0, "speaker": 3}]
    result = transcript.build_utterances(segments, turns)
    assert [(u["speaker"], u["text"]) for u in result] == [("Speaker 1", "hello there"), ("Speaker 2", "hi")]


def test_a_long_pause_starts_a_new_utterance():
    result = transcript.build_utterances(words(("one", 0.0, 0.5), ("two", 5.0, 5.5)), [])
    assert [u["text"] for u in result] == ["one", "two"]


def test_render_places_frames_and_real_time():
    utterances = [{"start": 10.0, "end": 12.0, "speaker": "Speaker 1", "text": "look here"}]
    shots = [{"time": 5.0, "file": "frames/00-00-05.jpg"}, {"time": 20.0, "file": "frames/00-00-20.jpg"}]
    lines = transcript.render(utterances, shots, datetime(2026, 1, 15, 9, 0, 0)).splitlines()
    assert "[00:00:05 | 09:00:05] (frame: frames/00-00-05.jpg)" in lines
    assert "[00:00:10 | 09:00:10] Speaker 1: look here" in lines
    assert lines[-1] == "[00:00:20 | 09:00:20] (frame: frames/00-00-20.jpg)"


def thumb(value):
    return np.full(frames.THUMB_WIDTH * frames.THUMB_HEIGHT, value, dtype=np.uint8)


def test_identical_frames_are_dropped_until_the_gap_runs_out():
    count = int(frames.MAX_GAP / frames.SAMPLE_EVERY) + 2
    kept = frames.select(np.stack([thumb(10)] * count), max_frames=10)
    assert [f["reason"] for f in kept] == ["start", "interval"]


def test_a_changed_frame_is_kept():
    kept = frames.select(np.stack([thumb(10), thumb(10), thumb(200)]), max_frames=10)
    assert [f["time"] for f in kept] == [0.0, 2 * frames.SAMPLE_EVERY]


def test_a_restless_webcam_is_ignored_but_a_new_slide_is_not():
    rng = np.random.default_rng(1)
    stack = np.stack([thumb(10) for _ in range(60)])
    tile = frames.THUMB_WIDTH * frames.THUMB_HEIGHT // 4
    stack[:, :tile] = rng.integers(0, 255, size=(60, tile), dtype=np.uint8)
    stack[30:, tile:] = 200
    kept = frames.select(stack, max_frames=20)
    assert [f["time"] for f in kept if f["reason"] == "change"] == [30 * frames.SAMPLE_EVERY]


def test_the_cap_keeps_the_strongest_changes():
    stack = np.stack([thumb(0), thumb(30), thumb(250), thumb(0)])
    kept = frames.select(stack, max_frames=2)
    assert len(kept) == 2
    assert kept == sorted(kept, key=lambda f: f["time"])


def test_parakeet_subwords_join_into_words():
    tokens = [SimpleNamespace(text=" hel", start=0.0, end=0.2), SimpleNamespace(text="lo", start=0.2, end=0.4), SimpleNamespace(text=" you", start=0.5, end=0.7)]
    assert parakeet_mlx.words_from(tokens) == [
        {"word": "hello", "start": 0.0, "end": 0.4},
        {"word": "you", "start": 0.5, "end": 0.7},
    ]


def test_sherpa_words_take_the_offset():
    result = parakeet_sherpa.words_from([" hel", "lo", " you"], [0.0, 0.2, 0.5], 10.0, 11.0)
    assert result == [
        {"word": "hello", "start": 10.0, "end": 10.5},
        {"word": "you", "start": 10.5, "end": 11.0},
    ]
