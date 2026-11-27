from datetime import date

from app.graph.blast_radius import compute_blast_radius
from app.history.store import SnapshotStore
from app.inventory.loader import load_inventory_from_text
from app.metrics import render_prometheus_metrics
from app.probes.models import ProbeResult


def test_duckdb_snapshot_and_prometheus_metrics(tmp_path):
    inv = load_inventory_from_text(
        """
resources:
  - id: cert-api
    kind: tls_cert
    target: api.example.com
    owner: SRE
services:
  - name: payments-api
    criticality: high
    depends_on:
      - resource: cert-api
        impact: "API TLS fails"
"""
    )
    results = {
        "cert-api": ProbeResult(
            resource_id="cert-api",
            kind="tls_cert",
            expires_on=date(2026, 12, 2),
            days_remaining=5,
            status="critical",
            detail="Expires soon",
        )
    }
    report = compute_blast_radius(inv, results, today=date(2026, 11, 27), window_days=14)

    store = SnapshotStore(tmp_path / "snapshots.duckdb")
    inserted = store.record_report(report)
    assert inserted == 1
    assert store.count_snapshots() == 1

    prom = render_prometheus_metrics(report)
    assert 'deadline_map_services_at_risk{window_days="14"} 1' in prom
    assert 'deadline_map_days_remaining{resource_id="cert-api",kind="tls_cert",status="critical",owner="SRE"} 5' in prom
