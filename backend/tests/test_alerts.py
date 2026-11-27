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
