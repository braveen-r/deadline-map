from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal
from pydantic import BaseModel


ProbeStatus = Literal["ok", "warning", "critical", "expired", "error"]


class ProbeResult(BaseModel):
    resource_id: str
    kind: str
    expires_on: date | None = None
    days_remaining: int | None = None
    status: ProbeStatus
    detail: str = ""
    checked_at: datetime = datetime.now(timezone.utc)


def classify_days(days_left: int, warning_days: int, critical_days: int) -> ProbeStatus:
    if days_left < 0:
        return "expired"
    if days_left <= critical_days:
        return "critical"
    if days_left <= warning_days:
        return "warning"
    return "ok"
