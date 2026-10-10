"""AI provider registry and streaming adapters.

DeepSeek and OpenAI share one OpenAI-compatible client. Anthropic uses its
own messages stream. API keys are passed in and never logged.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

SYSTEM_PROMPT = """你是 Weaveverse OS 的个人数字空间助手。
你的语气：友好、简洁、不啰嗦。中文优先。
不知道的就说不知道，不要编造。
不要提及 API Key、账号或自己的配置状态。
你可以调用工具。一次只调用一个。
可以直接用的只读工具：search_items、get_page_content、list_groups。
会改动数据的工具：create_page、create_quick_note、create_group。调用之后由界面请用户确认，你不要说已经创建成功。
不能修改、删除或移动已有内容。"""

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


def _raise_for_status(status_code: int) -> None:
    if status_code in {401, 403}:
        raise PermissionError("API Key 无效，请检查")
    if status_code >= 400:
        raise RuntimeError("网络错误，请重试")


def openai_tools(tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            },
        }
        for tool in tools
    ]


def anthropic_tools(tools: list[dict]) -> list[dict]:
    return [
        {"name": tool["name"], "description": tool["description"], "input_schema": tool["parameters"]}
        for tool in tools
    ]


async def complete_chat(
    *,
    kind: str,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
) -> dict:
    if kind == "anthropic":
        return await _anthropic_complete(base_url, api_key, model, messages, tools or [])
    return await _openai_complete(base_url, api_key, model, messages, tools or [])


def append_tool_result(kind: str, messages: list[dict], call: dict, result_text: str) -> list[dict]:
    if kind == "anthropic":
        return [
            *messages,
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": call["id"],
                        "name": call["name"],
                        "input": call["arguments"],
                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": call["id"], "content": result_text}],
            },
        ]
    return [
        *messages,
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": call["id"],
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": json.dumps(call["arguments"], ensure_ascii=False),
                    },
                }
            ],
        },
        {"role": "tool", "tool_call_id": call["id"], "content": result_text},
    ]


async def _openai_complete(base_url: str, api_key: str, model: str, messages: list[dict], tools: list[dict]) -> dict:
    payload = {
        "model": model,
        "stream": False,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
    }
    if tools:
        payload["tools"] = openai_tools(tools)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(_openai_url(base_url), headers=headers, json=payload)
    _raise_for_status(response.status_code)
    choice = (response.json().get("choices") or [{}])[0].get("message") or {}
    calls = []
    for call in choice.get("tool_calls") or []:
        function = call.get("function") or {}
        try:
            arguments = json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError:
            arguments = {}
        if not isinstance(arguments, dict):
            arguments = {}
        calls.append({"id": call.get("id") or "call", "name": function.get("name") or "", "arguments": arguments})
    return {"text": choice.get("content") or "", "calls": calls}


async def _anthropic_complete(base_url: str, api_key: str, model: str, messages: list[dict], tools: list[dict]) -> dict:
    payload = {
        "model": model,
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": messages,
    }
    if tools:
        payload["tools"] = anthropic_tools(tools)
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(_anthropic_url(base_url), headers=headers, json=payload)
    _raise_for_status(response.status_code)
    body = response.json()
    text = []
    calls = []
    for block in body.get("content") or []:
        if block.get("type") == "text" and block.get("text"):
            text.append(block["text"])
        if block.get("type") == "tool_use":
            arguments = block.get("input") if isinstance(block.get("input"), dict) else {}
            calls.append({"id": block.get("id") or "call", "name": block.get("name") or "", "arguments": arguments})
    return {"text": "".join(text), "calls": calls}


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
