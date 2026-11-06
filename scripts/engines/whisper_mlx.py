"""Whisper on Apple Silicon."""

from __future__ import annotations

name = "whisper-mlx"
default_model = "mlx-community/whisper-large-v3-turbo"


def transcribe(audio, model, language, vocabulary, log):
    import mlx_whisper

    result = mlx_whisper.transcribe(
        str(audio),
        path_or_hf_repo=model,
        language=language,
        word_timestamps=True,
        condition_on_previous_text=False,
        initial_prompt=", ".join(vocabulary) + "." if vocabulary else None,
    )
    return [
        {
            "start": round(s["start"], 2),
            "end": round(s["end"], 2),
            "text": s["text"].strip(),
            "words": [
                {"word": w["word"].strip(), "start": round(w["start"], 2), "end": round(w["end"], 2)}
                for w in s.get("words", [])
            ],
        }
        for s in result["segments"]
    ]
