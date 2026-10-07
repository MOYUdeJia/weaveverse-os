"""Helpers for the M2 API error body: {field, message}."""

from __future__ import annotations

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError


# 抛出带字段名的 API 错误。
# Raise an API error that names the failing field.
def raise_api_error(status_code: int, field: str, message: str) -> None:
    raise HTTPException(status_code=status_code, detail={"field": field, "message": message})


# 把 FastAPI 校验错误收成第一个字段和原因。
# Collapse a FastAPI validation error into the first field and reason.
def detail_from_validation_error(exc: RequestValidationError) -> dict[str, str]:
    errors = exc.errors()
    if not errors:
        return {"field": "body", "message": "请求参数错误"}

    first = errors[0]
    location = first.get("loc") or ("body",)
    field = str(location[-1]) if location else "body"
    message = str(first.get("msg") or "请求参数错误")
    return {"field": field, "message": message}
