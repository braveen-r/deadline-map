from datetime import date

from app.graph.blast_radius import compute_blast_radius, evaluate_manual_resource
from app.inventory.loader import load_inventory_from_text
from app.probes.models import ProbeResult


SAMPLE_YAML = """
version: 1
thresholds:
  warning_days: 30
  critical_days: 7
resources:
  - id: cert-main
    kind: tls_cert
    target: app.example.com
    owner: Platform
    renewal_hint: "Renew cert"
  - id: token-ci
    kind: token
    rotated_on: 2026-10-01
    rotation_days: 30
    owner: DevOps
    renewal_hint: "Rotate token"
services:
  - name: checkout-api
    criticality: high
    depends_on:
      - resource: cert-main
        impact: "HTTPS fails"
  - name: deploy-bot
    criticality: medium
    depends_on:
      - resource: token-ci
        impact: "Deployments stop"
"""


def test_blast_radius_sorts_critical_first_and_counts_services():
    today = date(2026, 11, 2)
    inv = load_inventory_from_text(SAMPLE_YAML)

    token_res = next(r for r in inv.resources if r.id == "token-ci")
    probe_results = {
        "cert-main": ProbeResult(
            resource_id="cert-main",
            kind="tls_cert",
            expires_on=date(2026, 11, 6),
            days_remaining=4,
            status="critical",
            detail="Expires in 4 days",
        ),
        "token-ci": evaluate_manual_resource(token_res, inv.thresholds, today),
    }

    report = compute_blast_radius(inv, probe_results, today=today, window_days=14)
    assert report.impacts[0].resource_id == "token-ci"
    assert report.impacts[0].status == "expired"
    assert report.impacts[1].resource_id == "cert-main"
    assert report.services_at_risk_count == 2
    assert report.deadlines_in_window_count == 2
