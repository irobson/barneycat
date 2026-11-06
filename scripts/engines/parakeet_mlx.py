"""NVIDIA Parakeet v3 on Apple Silicon. It takes no language hint and no vocabulary prompt."""

from __future__ import annotations

name = "parakeet-mlx"
default_model = "mlx-community/parakeet-tdt-0.6b-v3"
CHUNK_SECONDS = 120.0
OVERLAP_SECONDS = 15.0


def words_from(tokens) -> list[dict]:
    """Tokens are subwords, and a leading space marks the start of a new word."""
    words: list[dict] = []
    for token in tokens:
        if token.text.startswith(" ") or not words:
            words.append({"word": token.text.strip(), "start": round(token.start, 2), "end": round(token.end, 2)})
        else:
            words[-1]["word"] += token.text
            words[-1]["end"] = round(token.end, 2)
    return words


def transcribe(audio, model, language, vocabulary, log):
    from parakeet_mlx import from_pretrained

    result = from_pretrained(model).transcribe(
        str(audio), chunk_duration=CHUNK_SECONDS, overlap_duration=OVERLAP_SECONDS
    )
    return [
        {"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(), "words": words_from(s.tokens)}
        for s in result.sentences
    ]
