"""HTTP routes for AI settings and streaming chat. Keys are never returned."""

from __future__ import annotations

import json
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import ai_secrets
from app.ai_providers import PROVIDERS, append_tool_result, complete_chat, provider_spec, stream_chat
from app.ai_tools import TOOLS, is_write, run_tool, summarize_call
from sqlmodel import Session

from app.config import DATA_DIR
from app.db import get_session
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


class ToolResume(BaseModel):
    id: str = ""
    name: str
    arguments: dict = Field(default_factory=dict)
    approved: bool = False


class ChatRequest(BaseModel):
    messages: list[ChatTurn] = Field(min_length=1, max_length=30)
    resume: ToolResume | None = None


def _load_file() -> dict:
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_settings() -> dict:
    data = _load_file()
    profiles = data.get("profiles") if isinstance(data.get("profiles"), dict) else {}
    if not profiles and data.get("provider"):
        profiles = {
            str(data.get("provider")): {
                "base_url": data.get("base_url") or "",
                "model": data.get("model") or "",
            }
        }
    provider = str(data.get("provider") or "deepseek")
    if provider_spec(provider) is None:
        provider = "deepseek"
    spec = provider_spec(provider) or {}
    slot = profiles.get(provider) if isinstance(profiles.get(provider), dict) else {}
    base_url = str(slot.get("base_url") or spec.get("base_url") or "")
    model = str(slot.get("model") or (spec.get("models") or [""])[0])
    return {"provider": provider, "base_url": base_url, "model": model, "profiles": profiles}


def _write_settings(provider: str, base_url: str, model: str) -> dict:
    current = _read_settings()
    profiles = dict(current["profiles"])
    profiles[provider] = {"base_url": base_url, "model": model}
    payload = {"provider": provider, "profiles": profiles}
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return _read_settings()


def _profile_public(provider: str, profiles: dict) -> dict:
    spec = provider_spec(provider) or {}
    slot = profiles.get(provider) if isinstance(profiles.get(provider), dict) else {}
    models = spec.get("models") or [""]
    return {
        "base_url": str(slot.get("base_url") or spec.get("base_url") or ""),
        "model": str(slot.get("model") or models[0]),
        "has_key": ai_secrets.has_api_key(provider),
    }


def _public(settings: dict) -> dict:
    spec = provider_spec(settings["provider"]) or {}
    profiles = settings.get("profiles") or {}
    return {
        "provider": settings["provider"],
        "base_url": settings["base_url"],
        "model": settings["model"],
        "has_key": ai_secrets.has_api_key(settings["provider"]),
        "profiles": {key: _profile_public(key, profiles) for key in PROVIDERS},
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


def _event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _chunks(text: str):
    step = 24
    for index in range(0, len(text), step):
        yield text[index : index + step]


@router.post("/chat")
async def chat(data: ChatRequest, session: Session = Depends(get_session)):
    settings = _read_settings()
    spec = provider_spec(settings["provider"])
    key = ai_secrets.get_api_key(settings["provider"])
    if spec is None or not key:
        raise_api_error(400, "api_key", "请先在设置里配置 API Key")
    history = _clean_messages(data.messages)
    kind = spec["kind"]

    async def events():
        try:
            if data.resume is not None:
                result = (
                    run_tool(session, data.resume.name, data.resume.arguments)
                    if data.resume.approved
                    else {"ok": False, "error": "用户取消了这次操作"}
                )
                if data.resume.approved:
                    yield _event(
                        {
                            "tool": {
                                "name": data.resume.name,
                                "summary": result.get("summary") or summarize_call(data.resume.name, data.resume.arguments),
                                "ok": bool(result.get("ok")),
                                "group_id": result.get("group_id"),
                                "nav_id": result.get("id") if data.resume.name == "create_page" else None,
                            }
                        }
                    )
                history_with_tool = append_tool_result(
                    kind,
                    history,
                    {"id": data.resume.id or "call", "name": data.resume.name, "arguments": data.resume.arguments},
                    json.dumps(result, ensure_ascii=False),
                )
            else:
                history_with_tool = history
            working = history_with_tool
            for _round in range(4):
                turn = await complete_chat(
                    kind=kind,
                    base_url=settings["base_url"],
                    api_key=key,
                    model=settings["model"],
                    messages=working,
                    tools=TOOLS,
                )
                if not turn["calls"]:
                    for piece in _chunks(turn["text"] or ""):
                        yield _event({"text": piece})
                    break
                call = turn["calls"][0]
                if is_write(call["name"]):
                    yield _event(
                        {
                            "confirm": {
                                "id": call["id"],
                                "name": call["name"],
                                "arguments": call["arguments"],
                                "summary": summarize_call(call["name"], call["arguments"]),
                            }
                        }
                    )
                    break
                result = run_tool(session, call["name"], call["arguments"])
                yield _event({"status": summarize_call(call["name"], call["arguments"])})
                working = append_tool_result(kind, working, call, json.dumps(result, ensure_ascii=False)[:4000])
                if turn["text"]:
                    for piece in _chunks(turn["text"]):
                        yield _event({"text": piece})
        except PermissionError as exc:
            yield _event({"error": str(exc)})
        except Exception:
            yield _event({"error": "网络错误，请重试"})
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
