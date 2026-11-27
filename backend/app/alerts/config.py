from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def load_dotenv_file(env_path: Path = Path(".env")) -> None:
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def _clean(name: str) -> str | None:
    val = os.getenv(name, "").strip()
    return val or None


def _parse_alert_days() -> tuple[int, ...]:
    raw = os.getenv("ALERT_DAYS", "").strip()
    if not raw:
        return (30, 14, 7, 1)
    days = [int(part.strip()) for part in raw.split(",") if part.strip()]
    return tuple(days) if days else (30, 14, 7, 1)


def alert_config_from_env(env_path: Path = Path(".env")) -> dict[str, Any]:
    load_dotenv_file(env_path)
    return {
        "telegram_token": _clean("TELEGRAM_BOT_TOKEN"),
        "telegram_chat_id": _clean("TELEGRAM_CHAT_ID"),
        "discord_webhook_url": _clean("DISCORD_WEBHOOK_URL"),
        "slack_webhook_url": _clean("SLACK_WEBHOOK_URL"),
        "teams_webhook_url": _clean("TEAMS_WEBHOOK_URL"),
        "email_recipient": _clean("ALERT_EMAIL_RECIPIENT"),
        "smtp_host": _clean("SMTP_HOST") or "localhost",
        "alert_days": _parse_alert_days(),
    }
