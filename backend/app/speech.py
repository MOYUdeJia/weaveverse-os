"""Local speech recognition and Microsoft neural speech synthesis.

Models stay in backend/data/whisper_models. No API key is used.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.config import DATA_DIR

WHISPER_DIR = DATA_DIR / "whisper_models"
VOICES = [
    "zh-CN-XiaoxiaoNeural",
    "zh-CN-YunxiNeural",
    "zh-CN-XiaoyiNeural",
    "en-US-AriaNeural",
]
MODEL_SIZES = {"base", "small", "medium"}

_model = None
_model_size = ""


def transcribe(audio_path: Path, model_size: str) -> str:
    global _model, _model_size
    size = model_size if model_size in MODEL_SIZES else "base"
    WHISPER_DIR.mkdir(parents=True, exist_ok=True)
    from faster_whisper import WhisperModel

    if _model is None or _model_size != size:
        _model = WhisperModel(size, device="cpu", compute_type="int8", download_root=str(WHISPER_DIR))
        _model_size = size
    segments, _info = _model.transcribe(str(audio_path), language=None, vad_filter=True)
    return "".join(segment.text for segment in segments).strip()


async def synthesize(text: str, voice: str, rate: float) -> bytes:
    import edge_tts

    chosen = voice if voice in VOICES else VOICES[0]
    percent = max(-50, min(50, int(round((rate - 1) * 100))))
    communicate = edge_tts.Communicate(text[:2000], chosen, rate=f"{percent:+d}%")
    chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)


def synthesize_sync(text: str, voice: str, rate: float) -> bytes:
    return asyncio.run(synthesize(text, voice, rate))
