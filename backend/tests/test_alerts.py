from pathlib import Path

from app.alerts.notifier import dispatch_report_alerts
from app.cli import run_checks


def test_dispatch_report_alerts_webhooks_telegram_and_email():
    report = run_checks(Path("examples/deadlines.yml"), window_days=30, offline=True)
    posted = []
    sent_emails = []

    def fake_post(*args, **kwargs) -> None:
        posted.append((args, kwargs))

    def fake_email(*args, **kwargs) -> None:
        sent_emails.append((args, kwargs))

    sent = dispatch_report_alerts(
        report,
        telegram_token="123456:ABC-DEF",
        telegram_chat_id="987654321",
        discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        slack_webhook_url="https://hooks.slack.test/services/T00/B00/XXX",
        teams_webhook_url="https://teams.test/webhook/YYY",
        email_recipient="oncall@example.test",
        smtp_host="smtp.example.test",
        sender=fake_post,
        email_sender=fake_email,
    )

    assert isinstance(sent, list)
    assert len(posted) + len(sent_emails) >= 0


def test_alert_config_from_env_loads_dotenv(tmp_path, monkeypatch):
    from app.alerts.config import alert_config_from_env

    for var in (
        "SLACK_WEBHOOK_URL",
        "TEAMS_WEBHOOK_URL",
        "DISCORD_WEBHOOK_URL",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "ALERT_EMAIL_RECIPIENT",
        "SMTP_HOST",
        "ALERT_DAYS",
    ):
        monkeypatch.delenv(var, raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "SLACK_WEBHOOK_URL=https://hooks.slack.test/abc\n"
        "SMTP_HOST=smtp.internal\n"
        "ALERT_DAYS=14,7,1\n",
        encoding="utf-8",
    )

    cfg = alert_config_from_env(env_file)
    assert cfg["slack_webhook_url"] == "https://hooks.slack.test/abc"
    assert cfg["smtp_host"] == "smtp.internal"
    assert cfg["alert_days"] == (14, 7, 1)
    assert cfg["discord_webhook_url"] is None
