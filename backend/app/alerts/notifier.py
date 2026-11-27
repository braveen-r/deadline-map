from __future__ import annotations

from email.message import EmailMessage
import smtplib
from typing import Callable
import httpx

from app.graph.blast_radius import BlastRadiusReport, DeadlineImpact


AlertSender = Callable[[str, dict], int]
EmailSender = Callable[[str, str, str, str], None]

DEFAULT_ALERT_DAYS: tuple[int, ...] = (30, 14, 7, 1)


def default_post_json(url: str, payload: dict) -> int:
    with httpx.Client(timeout=8.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.status_code


def default_send_email(smtp_host: str, recipient: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = f"deadline-map@{smtp_host}"
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(smtp_host, 25, timeout=8.0) as smtp:
        smtp.send_message(msg)


def should_alert(impact: DeadlineImpact, alert_days: tuple[int, ...] = DEFAULT_ALERT_DAYS) -> bool:
    if impact.status in {"expired", "error"}:
        return True
    if impact.days_remaining is None:
        return False
    return impact.days_remaining in alert_days or impact.days_remaining <= max(alert_days)


def format_alert_message(impact: DeadlineImpact) -> str:
    days_text = (
        f"overdue by {abs(impact.days_remaining)}d"
        if impact.days_remaining is not None and impact.days_remaining < 0
        else (f"in {impact.days_remaining}d" if impact.days_remaining is not None else "unknown days")
    )
    services_text = (
        ", ".join(f"{s.service_name} ({s.impact})" for s in impact.affected_services)
        if impact.affected_services
        else "no mapped services"
    )
    hint_line = f"\nRecommended action: {impact.renewal_hint}" if impact.renewal_hint else ""
    return (
        f"[{impact.status.upper()} · severity={impact.severity}] {impact.resource_id} ({impact.kind}) — {days_text}\n"
        f"Owner: {impact.owner} | Priority: {impact.priority_score}\n"
        f"Breaks: {services_text}{hint_line}"
    )


def send_telegram_alert(bot_token: str, chat_id: str, message: str, sender: AlertSender = default_post_json) -> int:
    return sender(f"https://api.telegram.org/bot{bot_token}/sendMessage", {"chat_id": chat_id, "text": message})


def send_discord_alert(webhook_url: str, message: str, sender: AlertSender = default_post_json) -> int:
    return sender(webhook_url, {"content": message})


def send_slack_alert(webhook_url: str, message: str, sender: AlertSender = default_post_json) -> int:
    return sender(webhook_url, {"text": message})


def send_teams_alert(webhook_url: str, message: str, sender: AlertSender = default_post_json) -> int:
    return sender(webhook_url, {"text": message})


def dispatch_report_alerts(
    report: BlastRadiusReport,
    telegram_token: str | None = None,
    telegram_chat_id: str | None = None,
    discord_webhook_url: str | None = None,
    slack_webhook_url: str | None = None,
    teams_webhook_url: str | None = None,
    email_recipient: str | None = None,
    smtp_host: str = "localhost",
    alert_days: tuple[int, ...] = DEFAULT_ALERT_DAYS,
    sender: AlertSender = default_post_json,
    email_sender: EmailSender = default_send_email,
) -> list[str]:
    sent_messages: list[str] = []
    for item in report.impacts:
        if not should_alert(item, alert_days=alert_days):
            continue
        msg = format_alert_message(item)
        if telegram_token and telegram_chat_id:
            send_telegram_alert(telegram_token, telegram_chat_id, msg, sender=sender)
        if discord_webhook_url:
            send_discord_alert(discord_webhook_url, msg, sender=sender)
        if slack_webhook_url:
            send_slack_alert(slack_webhook_url, msg, sender=sender)
        if teams_webhook_url:
            send_teams_alert(teams_webhook_url, msg, sender=sender)
        if email_recipient:
            email_sender(smtp_host, email_recipient, f"[deadline-map] {item.resource_id} ({item.status})", msg)
        sent_messages.append(msg)
    return sent_messages
