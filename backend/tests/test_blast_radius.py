from datetime import date

from app.graph.blast_radius import classify_days, compute_blast_radius
from app.inventory.loader import load_inventory_file


def test_classify_days_thresholds():
    assert classify_days(0) == "critical"
    assert classify_days(7) == "critical"
    assert classify_days(14) == "warning"
    assert classify_days(45) == "healthy"


def test_blast_radius_sorts_critical_first_and_counts_services():
    inv = load_inventory_file("examples/deadlines.yml")
    report = compute_blast_radius(inv, as_of=date(2026, 11, 27), window_days=30, offline=True)

    assert len(report.impacts) >= 1
    assert 0 <= report.health_score <= 100

    severities = [item.severity for item in report.impacts]
    if "critical" in severities and "warning" in severities:
        assert severities.index("critical") < severities.index("warning")
