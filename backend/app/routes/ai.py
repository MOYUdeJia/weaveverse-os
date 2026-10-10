"""HTTP routes for AI settings and streaming chat. Keys are never returned."""

from __future__ import annotations

import json
from urllib.parse import urlsplit

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import ai_secrets
from app.ai_providers import PROVIDERS, provider_spec, stream_chat
from app.config import DATA_DIR
from app.errors import raise_api_error

router = APIRouter(prefix="/ai", tags=["ai"])

_SETTINGS_PATH = DATA_DIR / "ai_settings.json"


class AiSettingsWrite(BaseModel):
    provider: str = Field(min_length=1, max_length=32)
    base_url: str = Field(min_length=8, max_length=200)
    model: str = Field(min_length=1, max_length=80)
    api_key: str = Field(default="", max_length=300)


class ChatTurn(BaseModel):
    role: str
    content: str = Field(max_length=8000)


class ChatRequest(BaseModel):
    messages: list[ChatTurn] = Field(min_length=1, max_length=30)


def _read_settings() -> dict:
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    provider = str(data.get("provider") or "deepseek")
    spec = provider_spec(provider) or provider_spec("deepseek")
    provider = provider if provider_spec(provider) else "deepseek"
    base_url = str(data.get("base_url") or spec["base_url"])
    model = str(data.get("model") or spec["models"][0])
    return {"provider": provider, "base_url": base_url, "model": model}


def _write_settings(provider: str, base_url: str, model: str) -> dict:
    payload = {"provider": provider, "base_url": base_url, "model": model}
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _public(settings: dict) -> dict:
    spec = provider_spec(settings["provider"]) or {}
    return {
        "provider": settings["provider"],
        "base_url": settings["base_url"],
        "model": settings["model"],
        "has_key": ai_secrets.has_api_key(settings["provider"]),
        "providers": [
            {
                "id": key,
                "label": item["label"],
                "base_url": item["base_url"],
                "models": item["models"],
            }
            for key, item in PROVIDERS.items()
        ],
        "label": spec.get("label") or settings["provider"],
    }


def _check_url(base_url: str) -> str:
    parsed = urlsplit(base_url.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise_api_error(400, "base_url", "Base URL 需要是 https 地址")
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def _clean_messages(rows: list[ChatTurn]) -> list[dict]:
    cleaned = []
    for row in rows:
        role = "assistant" if row.role == "assistant" else "user"
        text = row.content.strip()
        if text:
            cleaned.append({"role": role, "content": text})
    if not cleaned or cleaned[-1]["role"] != "user":
        raise_api_error(400, "messages", "需要一条用户消息")
    return cleaned[-20:]


@router.get("/settings")
def get_settings() -> dict:
    return _public(_read_settings())


@router.put("/settings")
def put_settings(data: AiSettingsWrite) -> dict:
    spec = provider_spec(data.provider)
    if spec is None:
        raise_api_error(400, "provider", "未知的提供商")
    base_url = _check_url(data.base_url)
    model = data.model.strip()
    settings = _write_settings(data.provider, base_url, model)
    key = data.api_key.strip()
    if key:
        ai_secrets.set_api_key(data.provider, key)
    return _public(settings)


@router.post("/test")
async def test_connection() -> dict:
    settings = _read_settings()
    spec = provider_spec(settings["provider"])
    key = ai_secrets.get_api_key(settings["provider"])
    if spec is None or not key:
        raise_api_error(400, "api_key", "请先在设置里配置 API Key")
    try:
        async for _piece in stream_chat(
            kind=spec["kind"],
            base_url=settings["base_url"],
            api_key=key,
            model=settings["model"],
            messages=[{"role": "user", "content": "回复一个字：好"}],
        ):
            break
    except PermissionError as exc:
        raise_api_error(401, "api_key", str(exc))
    except Exception:
        raise_api_error(502, "network", "网络错误，请重试")
    return {"ok": True}


@router.post("/chat")
async def chat(data: ChatRequest):
    settings = _read_settings()
    spec = provider_spec(settings["provider"])
    key = ai_secrets.get_api_key(settings["provider"])
    if spec is None or not key:
        raise_api_error(400, "api_key", "请先在设置里配置 API Key")
    messages = _clean_messages(data.messages)

    async def events():
        try:
            async for piece in stream_chat(
                kind=spec["kind"],
                base_url=settings["base_url"],
                api_key=key,
                model=settings["model"],
                messages=messages,
            ):
                yield f"data: {json.dumps({'text': piece}, ensure_ascii=False)}\n\n"
        except PermissionError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"
        except Exception:
            yield 'data: {"error": "网络错误，请重试"}\n\n'
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
