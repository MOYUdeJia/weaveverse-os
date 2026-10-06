"""HTTP routes for sidebar navigation CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app import crud
from app.db import get_session
from app.schemas import NavItemCreate, NavItemRead, NavItemUpdate


router = APIRouter(prefix="/nav", tags=["nav"])


@router.get("", response_model=list[NavItemRead])
def get_nav(session: Session = Depends(get_session)) -> list:
    return crud.list_nav_items(session)


@router.post("", response_model=NavItemRead)
def create_nav(data: NavItemCreate, session: Session = Depends(get_session)):
    return crud.create_nav_item(session, data)


@router.put("/{nav_id}", response_model=NavItemRead)
def update_nav(nav_id: int, data: NavItemUpdate, session: Session = Depends(get_session)):
    item = crud.get_nav_item(session, nav_id)
    if item is None:
        raise HTTPException(status_code=404, detail="导航项不存在")
    return crud.update_nav_item(session, item, data)


@router.delete("/{nav_id}")
def delete_nav(nav_id: int, session: Session = Depends(get_session)) -> dict[str, str]:
    item = crud.get_nav_item(session, nav_id)
    if item is None:
        raise HTTPException(status_code=404, detail="导航项不存在")
    crud.delete_nav_item(session, item)
    return {"status": "ok"}
