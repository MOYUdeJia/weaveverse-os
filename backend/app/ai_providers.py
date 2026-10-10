"""AI provider registry and streaming adapters.

DeepSeek and OpenAI share one OpenAI-compatible client. Anthropic uses its
own messages stream. API keys are passed in and never logged.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

SYSTEM_PROMPT = """你是 Weaveverse OS 的个人数字空间助手。
你的角色：帮助用户整理思路、回答问题、查找信息。
你的语气：友好、简洁、不啰嗦。中文优先。
你的能力边界（M8 阶段）：你只能聊天，不能操作用户的数据。
未来会支持：帮用户创建页面、搜索笔记、总结内容。
不知道的就说不知道，不要编造。"""

PROVIDERS = {
    "deepseek": {
        "label": "DeepSeek",
        "kind": "openai",
        "base_url": "https://api.deepseek.com",
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "openai": {
        "label": "OpenAI",
        "kind": "openai",
        "base_url": "https://api.openai.com",
        "models": ["gpt-4o-mini", "gpt-4o"],
    },
    "anthropic": {
        "label": "Anthropic",
        "kind": "anthropic",
        "base_url": "https://api.anthropic.com",
        "models": ["claude-sonnet-4-5", "claude-3-5-haiku-latest"],
    },
}


def provider_spec(provider: str) -> dict | None:
    return PROVIDERS.get(provider)


def _openai_url(base_url: str) -> str:
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        return f"{root}/chat/completions"
    return f"{root}/v1/chat/completions"


def _anthropic_url(base_url: str) -> str:
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        return f"{root}/messages"
    return f"{root}/v1/messages"


async def stream_chat(
    *,
    kind: str,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
) -> AsyncIterator[str]:
    if kind == "anthropic":
        async for piece in _anthropic_stream(base_url, api_key, model, messages):
            yield piece
        return
    async for piece in _openai_stream(base_url, api_key, model, messages):
        yield piece


async def _openai_stream(base_url: str, api_key: str, model: str, messages: list[dict]) -> AsyncIterator[str]:
    payload = {
        "model": model,
        "stream": True,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", _openai_url(base_url), headers=headers, json=payload) as response:
            if response.status_code in {401, 403}:
                raise PermissionError("API Key 无效，请检查")
            if response.status_code >= 400:
                raise RuntimeError("网络错误，请重试")
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = (choices[0].get("delta") or {}).get("content") or ""
                if delta:
                    yield delta


async def _anthropic_stream(base_url: str, api_key: str, model: str, messages: list[dict]) -> AsyncIterator[str]:
    payload = {
        "model": model,
        "max_tokens": 1024,
        "stream": True,
        "system": SYSTEM_PROMPT,
        "messages": messages,
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", _anthropic_url(base_url), headers=headers, json=payload) as response:
            if response.status_code in {401, 403}:
                raise PermissionError("API Key 无效，请检查")
            if response.status_code >= 400:
                raise RuntimeError("网络错误，请重试")
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                try:
                    chunk = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                delta = chunk.get("delta") or {}
                text = delta.get("text") or ""
                if text:
                    yield text
