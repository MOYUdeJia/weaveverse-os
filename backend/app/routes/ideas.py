"""HTTP routes for the idea box, including short AI helpers."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlmodel import Session

from app import ai_secrets, idea_crud
from app.ai_providers import complete_chat, provider_spec
from app.db import get_session
from app.errors import raise_api_error
from app.routes.ai import _read_settings

router = APIRouter(prefix="/ideas", tags=["ideas"])


class IdeaWrite(BaseModel):
    title: str = Field(default="", max_length=80)
    content: str = Field(default="", max_length=8000)
    tags: list[str] = Field(default_factory=list)

    def cleaned_tags(self) -> list[str]:
        cleaned = []
        for raw in self.tags:
            text = str(raw).strip().lstrip("#")
            if text and text not in cleaned:
                cleaned.append(text[:24])
        return cleaned[:8]


class IdeaPatch(BaseModel):
    title: str | None = Field(default=None, max_length=80)
    content: str | None = Field(default=None, max_length=8000)
    tags: list[str] | None = None


def _require_model() -> tuple[dict, dict, str]:
    settings = _read_settings()
    spec = provider_spec(settings["provider"])
    key = ai_secrets.get_api_key(settings["provider"])
    if spec is None or not key:
        raise_api_error(400, "api_key", "请先在设置里配置 API Key")
    return settings, spec, key


@router.get("")
def list_ideas(session: Session = Depends(get_session)) -> list[dict]:
    return [idea_crud.idea_to_dict(row) for row in idea_crud.list_ideas(session)]


@router.post("")
def create_idea(data: IdeaWrite, session: Session = Depends(get_session)) -> dict:
    if not data.content.strip() and not data.title.strip():
        raise_api_error(400, "content", "写一点内容")
    row = idea_crud.create_idea(session, data.title.strip(), data.content.strip(), data.cleaned_tags())
    return idea_crud.idea_to_dict(row)


@router.patch("/{idea_id}")
def update_idea(idea_id: int, data: IdeaPatch, session: Session = Depends(get_session)) -> dict:
    row = idea_crud.get_idea(session, idea_id)
    if row is None:
        raise_api_error(404, "id", "点子不存在")
    tags = None
    if data.tags is not None:
        tags = IdeaWrite(tags=data.tags).cleaned_tags()
    updated = idea_crud.update_idea(
        session,
        row,
        None if data.title is None else data.title.strip(),
        None if data.content is None else data.content.strip(),
        tags,
    )
    return idea_crud.idea_to_dict(updated)


@router.delete("/{idea_id}")
def delete_idea(idea_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    row = idea_crud.get_idea(session, idea_id)
    if row is None:
        raise_api_error(404, "id", "点子不存在")
    idea_crud.delete_idea(session, row)
    return {"status": "ok"}


async def _ask(prompt: str) -> str:
    settings, spec, key = _require_model()
    turn = await complete_chat(
        kind=spec["kind"],
        base_url=settings["base_url"],
        api_key=key,
        model=settings["model"],
        messages=[{"role": "user", "content": prompt}],
        tools=None,
    )
    return (turn.get("text") or "").strip()


@router.post("/{idea_id}/summary")
async def summarize_idea(idea_id: int, session: Session = Depends(get_session)) -> dict:
    row = idea_crud.get_idea(session, idea_id)
    if row is None:
        raise_api_error(404, "id", "点子不存在")
    text = await _ask(f"用两三句中文总结这个点子，不要加标题：\n{row.title}\n{row.content}")
    return {"summary": text}


@router.post("/{idea_id}/tags")
async def tag_idea(idea_id: int, session: Session = Depends(get_session)) -> dict:
    row = idea_crud.get_idea(session, idea_id)
    if row is None:
        raise_api_error(404, "id", "点子不存在")
    raw = await _ask(f"从下面的点子提取最多 4 个中文关键词，只用逗号分隔，不要解释：\n{row.title}\n{row.content}")
    tags = [part.strip().lstrip("#") for part in re.split(r"[,，、\s]+", raw) if part.strip()]
    tags = IdeaWrite(tags=tags).cleaned_tags()
    updated = idea_crud.update_idea(session, row, None, None, tags)
    return idea_crud.idea_to_dict(updated)
