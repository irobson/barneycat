"""NVIDIA Parakeet v3 on any CPU through sherpa-onnx.

The model cannot take an hour of audio at once, so voice activity detection splits it
into speech regions first. The model takes no language hint and no vocabulary prompt.
"""

from __future__ import annotations

import os

import config
import downloads
import media

name = "parakeet-sherpa"
default_model = "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8"
RELEASES = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models"
WINDOW = 512
MAX_SPEECH_SECONDS = 25.0


def speech_regions(samples, vad_model):
    import sherpa_onnx

    settings = sherpa_onnx.VadModelConfig()
    settings.silero_vad.model = str(vad_model)
    settings.silero_vad.min_silence_duration = 0.4
    settings.silero_vad.max_speech_duration = MAX_SPEECH_SECONDS
    settings.sample_rate = media.SAMPLE_RATE
    detector = sherpa_onnx.VoiceActivityDetector(settings, buffer_size_in_seconds=60)

    for offset in range(0, len(samples), WINDOW):
        detector.accept_waveform(samples[offset : offset + WINDOW])
        while not detector.empty():
            yield detector.front.start, detector.front.samples
            detector.pop()
    detector.flush()
    while not detector.empty():
        yield detector.front.start, detector.front.samples
        detector.pop()


def words_from(tokens, stamps, offset, end) -> list[dict]:
    """Tokens are subwords, and a leading space marks the start of a new word."""
    words: list[dict] = []
    for token, stamp in zip(tokens, stamps):
        moment = round(offset + stamp, 2)
        if token.startswith(" ") or not words:
            if words:
                words[-1]["end"] = moment
            words.append({"word": token.strip(), "start": moment, "end": moment})
        else:
            words[-1]["word"] += token
    if words:
        words[-1]["end"] = round(end, 2)
    return words


def transcribe(audio, model, language, vocabulary, log):
    import sherpa_onnx

    folder = downloads.archive(f"{RELEASES}/{model}.tar.bz2", config.models_dir(), log)
    vad_model = downloads.file(f"{RELEASES}/silero_vad.onnx", config.models_dir(), log)
    recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(folder / "encoder.int8.onnx"),
        decoder=str(folder / "decoder.int8.onnx"),
        joiner=str(folder / "joiner.int8.onnx"),
        tokens=str(folder / "tokens.txt"),
        num_threads=os.cpu_count() or 4,
        model_type="nemo_transducer",
    )

    segments = []
    for start, samples in speech_regions(media.read_wav(audio), vad_model):
        stream = recognizer.create_stream()
        stream.accept_waveform(media.SAMPLE_RATE, samples)
        recognizer.decode_stream(stream)
        text = stream.result.text.strip()
        if not text:
            continue
        offset = start / media.SAMPLE_RATE
        end = offset + len(samples) / media.SAMPLE_RATE
        segments.append({
            "start": round(offset, 2),
            "end": round(end, 2),
            "text": text,
            "words": words_from(stream.result.tokens, stream.result.timestamps, offset, end),
        })
    return segments
