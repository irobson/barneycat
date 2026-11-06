"""Local speaker diarization with sherpa-onnx. Needs no third-party token."""

from __future__ import annotations

import os
from pathlib import Path

import config
import downloads
import media

RELEASES = "https://github.com/k2-fsa/sherpa-onnx/releases/download"
SEGMENTATION = f"{RELEASES}/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2"
EMBEDDING = f"{RELEASES}/speaker-recongition-models/wespeaker_en_voxceleb_resnet34_LM.onnx"
CLUSTER_THRESHOLD = 0.5


def diarize(audio: Path, log=print) -> list[dict]:
    import sherpa_onnx

    folder = downloads.archive(SEGMENTATION, config.models_dir(), log)
    embedding = downloads.file(EMBEDDING, config.models_dir(), log)
    threads = os.cpu_count() or 4

    settings = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(folder / "model.onnx")),
            num_threads=threads,
        ),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(embedding), num_threads=threads),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=-1, threshold=CLUSTER_THRESHOLD),
        min_duration_on=0.3,
        min_duration_off=0.5,
    )
    if not settings.validate():
        raise RuntimeError("invalid diarization configuration")

    result = sherpa_onnx.OfflineSpeakerDiarization(settings).process(media.read_wav(audio))
    return [
        {"start": round(turn.start, 2), "end": round(turn.end, 2), "speaker": int(turn.speaker)}
        for turn in result.sort_by_start_time()
    ]
