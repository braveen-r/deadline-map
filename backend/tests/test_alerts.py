from datetime import date
from pathlib import Path

from app.alerts.notifier import dispatch_report_alerts
from app.graph.blast_radius import compute_blast_radius
from app.inventory.loader import load_inventory_file


def _sample_report():
    inv = load_inventory_file(Path("examples/deadlines.yml"))
    return compute_blast_radius(inv, as_of=date(2026, 11, 27), window_days=30, offline=True)


def test_dispatch_report_alerts_webhooks_telegram_and_email():
    report = _sample_report()
    posted = []
    sent_emails = []

    def fake_post(url: str, payload: dict) -> None:
        posted.append((url, payload))

    def fake_email(msg) -> None:
        sent_emails.append(msg)

    result = dispatch_report_alerts(
        report,
        slack_webhook_url="https://hooks.slack.test/services/T00/B00/XXX",
        teams_webhook_url="https://teams.test/webhook/YYY",
        discord_webhook_url="https://discord.com/api/webhooks/123/abc",
        telegram_bot_token="123456:ABC-DEF",
        telegram_chat_id="987654321",
        smtp_config={
            "host": "smtp.example.test",
            "port": 587,
            "to": "oncall@example.test",
            "from": "alerts@example.test",
        },
        post_json=fake_post,
        send_email=fake_email,
    )

    assert isinstance(result, dict)
    assert len(posted) >= 1 or len(sent_emails) >= 1
