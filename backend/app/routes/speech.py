"""Speech routes. Audio in, text or audio out. Keys are not involved."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.config import DATA_DIR
from app.errors import raise_api_error
from app.speech import MODEL_SIZES, VOICES, synthesize, transcribe

router = APIRouter(prefix="/speech", tags=["speech"])
_SETTINGS = DATA_DIR / "ai_settings.json"


class SpeechWrite(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


def voice_settings() -> dict:
    try:
        data = json.loads(_SETTINGS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    voice = data.get("voice") if isinstance(data, dict) and isinstance(data.get("voice"), dict) else {}
    model = str(voice.get("stt_model") or "base")
    name = str(voice.get("tts_voice") or VOICES[0])
    try:
        rate = float(voice.get("tts_rate") or 1)
    except (TypeError, ValueError):
        rate = 1
    return {
        "stt_model": model if model in MODEL_SIZES else "base",
        "tts_voice": name if name in VOICES else VOICES[0],
        "tts_rate": min(1.5, max(0.5, rate)),
        "voices": VOICES,
        "models": sorted(MODEL_SIZES),
    }


def save_voice_settings(stt_model: str, tts_voice: str, tts_rate: float) -> dict:
    try:
        data = json.loads(_SETTINGS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data["voice"] = {
        "stt_model": stt_model if stt_model in MODEL_SIZES else "base",
        "tts_voice": tts_voice if tts_voice in VOICES else VOICES[0],
        "tts_rate": min(1.5, max(0.5, tts_rate)),
    }
    _SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return voice_settings()


class VoiceWrite(BaseModel):
    stt_model: str = "base"
    tts_voice: str = VOICES[0]
    tts_rate: float = 1


@router.get("/settings")
def get_voice() -> dict:
    return voice_settings()


@router.put("/settings")
def put_voice(data: VoiceWrite) -> dict:
    return save_voice_settings(data.stt_model, data.tts_voice, data.tts_rate)


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile) -> dict:
    payload = await file.read()
    if not payload:
        raise_api_error(400, "file", "没有录到声音")
    settings = voice_settings()
    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    with NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(payload)
        path = Path(handle.name)
    try:
        text = transcribe(path, settings["stt_model"])
    except Exception:
        raise_api_error(502, "speech", "识别失败。如果是第一次，模型可能还在下载。")
    finally:
        path.unlink(missing_ok=True)
    return {"text": text, "downloading": False}


@router.post("/speak")
async def speak(data: SpeechWrite) -> Response:
    settings = voice_settings()
    try:
        audio = await synthesize(data.text, settings["tts_voice"], settings["tts_rate"])
    except Exception:
        raise_api_error(502, "speech", "朗读失败。需要能访问微软语音服务。")
    if not audio:
        raise_api_error(502, "speech", "朗读失败。需要能访问微软语音服务。")
    return Response(audio, media_type="audio/mpeg")
