"""Whisper through CTranslate2, on NVIDIA GPUs or the CPU."""

from __future__ import annotations

name = "whisper-faster"
default_model = "large-v3-turbo"


def transcribe(audio, model, language, vocabulary, log):
    from faster_whisper import WhisperModel

    import media
    from engines import has_cuda

    device, compute = ("cuda", "float16") if has_cuda() else ("cpu", "int8")
    segments, _ = WhisperModel(model, device=device, compute_type=compute).transcribe(
        # Samples, not a path: the file path goes through PyAV, which breaks across versions.
        media.read_wav(audio),
        language=language,
        word_timestamps=True,
        vad_filter=True,
        condition_on_previous_text=False,
        initial_prompt=", ".join(vocabulary) + "." if vocabulary else None,
    )
    return [
        {
            "start": round(s.start, 2),
            "end": round(s.end, 2),
            "text": s.text.strip(),
            "words": [{"word": w.word.strip(), "start": round(w.start, 2), "end": round(w.end, 2)} for w in s.words or []],
        }
        for s in segments
    ]
