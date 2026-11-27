from datetime import date

from app.alerts.notifier import dispatch_report_alerts, format_alert_message
from app.graph.blast_radius import compute_blast_radius
from app.inventory.loader import load_inventory_from_text
from app.probes.models import ProbeResult


def test_dispatch_alerts_sends_to_telegram_and_discord():
    inv = load_inventory_from_text(
        """
resources:
  - id: cert-prod
    kind: tls_cert
    target: prod.example.com
    owner: Braveen R
    renewal_hint: "Renew TLS certificate"
  - id: domain-far
    kind: domain
    target: far.example.com
    owner: Braveen R
services:
  - name: web-app
    criticality: high
    depends_on:
      - resource: cert-prod
        impact: "HTTPS fails"
"""
    )
    results = {
        "cert-prod": ProbeResult(
            resource_id="cert-prod",
            kind="tls_cert",
            expires_on=date(2026, 12, 4),
            days_remaining=7,
            status="critical",
            detail="Expires in 7 days",
        ),
        "domain-far": ProbeResult(
            resource_id="domain-far",
            kind="domain",
            expires_on=date(2027, 11, 27),
            days_remaining=365,
            status="ok",
            detail="Expires in 365 days",
        ),
    }
    report = compute_blast_radius(inv, results, today=date(2026, 11, 27), window_days=14)
    formatted = format_alert_message(report.impacts[0])
    assert "cert-prod" in formatted
    assert "web-app (HTTPS fails)" in formatted

    calls: list[tuple[str, dict]] = []

    def fake_sender(url: str, payload: dict) -> int:
        calls.append((url, payload))
        return 200

    dispatched = dispatch_report_alerts(
        report,
        telegram_token="fake-token",
        telegram_chat_id="12345",
        discord_webhook_url="https://discord.example/webhook",
        sender=fake_sender,
    )
    assert len(dispatched) == 1
    assert len(calls) == 2
