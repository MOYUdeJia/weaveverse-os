"""Remote access status. Reads Tailscale and draws a QR code. Does not change Tailscale."""

from __future__ import annotations

import segno

from fastapi import APIRouter

from app.remote_status import tailscale_status

router = APIRouter(prefix="/remote", tags=["remote"])


@router.get("")
def get_remote() -> dict:
    status = tailscale_status()
    svg = ""
    if status["url"]:
        svg = segno.make(status["url"], error="m").svg_inline(scale=4)
    return {**status, "qr": svg}
