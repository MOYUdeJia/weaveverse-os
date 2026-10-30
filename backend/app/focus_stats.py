"""Focus rounds summed for the stats sheet."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.models import FocusSession


def _local(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone()


def _parse_day(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return fallback


def _bucket(hour: int) -> str:
    if 5 <= hour < 12:
        return "上午"
    if 12 <= hour < 18:
        return "下午"
    return "夜间"


def summarize_focus(session: Session, start: str | None = None, end: str | None = None) -> dict:
    today = datetime.now().astimezone().date()
    start_day = _parse_day(start, today - timedelta(days=today.weekday() + 15 * 7))
    end_day = _parse_day(end, today)
    if end_day < start_day:
        start_day, end_day = end_day, start_day

    rows = session.exec(select(FocusSession)).all()
    chosen = []
    for row in rows:
        if row.completed_at is None:
            continue
        day = _local(row.completed_at).date()
        if start_day <= day <= end_day:
            chosen.append(row)

    done = [row for row in chosen if (row.outcome or "done") == "done"]
    abandoned = [row for row in chosen if row.outcome == "abandoned"]
    minutes = sum(int(row.minutes or 0) for row in done)
    span = (end_day - start_day).days + 1
    by_day: dict[str, dict] = {}
    by_cat: dict[str, int] = {}
    by_hour = {"上午": 0, "下午": 0, "夜间": 0}
    by_interrupt: dict[str, int] = {}
    week = [[0 for _ in range(12)] for _ in range(7)]

    for row in done:
        local = _local(row.completed_at)
        key = local.date().isoformat()
        cell = by_day.setdefault(key, {"minutes": 0, "count": 0})
        cell["minutes"] += int(row.minutes or 0)
        cell["count"] += 1
        cat = row.category or "未分类"
        by_cat[cat] = by_cat.get(cat, 0) + 1
        part = _bucket(local.hour)
        by_hour[part] += 1
        week_start = end_day - timedelta(days=end_day.weekday())
        if week_start <= local.date() <= week_start + timedelta(days=6):
            slot = min(11, local.hour // 2)
            week[local.weekday()][slot] += 1

    for row in abandoned:
        reason = row.interrupt or "没写原因"
        by_interrupt[reason] = by_interrupt.get(reason, 0) + 1

    days = []
    cursor = start_day
    while cursor <= end_day:
        key = cursor.isoformat()
        cell = by_day.get(key, {"minutes": 0, "count": 0})
        days.append(
            {
                "date": key,
                "minutes": cell["minutes"],
                "count": cell["count"],
                "future": cursor > today,
            }
        )
        cursor += timedelta(days=1)

    peak = max(by_hour, key=by_hour.get)
    if sum(by_hour.values()) == 0:
        peak = ""
    total_count = len(done)
    history = [
        {
            "id": row.id,
            "label": row.label,
            "minutes": row.minutes,
            "category": row.category,
            "outcome": row.outcome or "done",
            "interrupt": row.interrupt,
            "at": _local(row.completed_at).isoformat(timespec="minutes"),
        }
        for row in sorted(chosen, key=lambda item: item.completed_at or datetime.min, reverse=True)[:40]
    ]
    return {
        "start": start_day.isoformat(),
        "end": end_day.isoformat(),
        "today_minutes": by_day.get(today.isoformat(), {}).get("minutes", 0),
        "count": total_count,
        "minutes": minutes,
        "daily_average": round(minutes / span) if span else 0,
        "abandoned": len(abandoned),
        "completion": {
            "done": total_count,
            "abandoned": len(abandoned),
        },
        "peak": peak,
        "hours": by_hour,
        "categories": [{"name": name, "count": count} for name, count in by_cat.items()],
        "interrupts": [{"name": name, "count": count} for name, count in by_interrupt.items()],
        "week": week,
        "days": days,
        "history": history,
    }


def export_csv(session: Session, start: str | None = None, end: str | None = None) -> str:
    data = summarize_focus(session, start, end)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["时间", "名称", "分钟", "分类", "结果", "打断"])
    for row in data["history"]:
        writer.writerow([row["at"], row["label"], row["minutes"], row["category"], row["outcome"], row["interrupt"]])
    return buffer.getvalue()
