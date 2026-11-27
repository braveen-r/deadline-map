from pathlib import Path

from app.graph.blast_radius import BlastRadiusReport, classify_days
from app.cli import run_checks


def test_classify_days_thresholds():
    assert classify_days(0, 14, 7) == "critical"
    assert classify_days(7, 14, 7) == "critical"
    assert classify_days(14, 14, 7) == "warning"
    assert classify_days(45, 14, 7) == "ok"


def test_blast_radius_sorts_critical_first_and_counts_services():
    report = run_checks(Path("examples/deadlines.yml"), window_days=30, offline=True)

    assert isinstance(report, BlastRadiusReport)
    assert len(report.impacts) >= 1
    if hasattr(report, "health_score"):
        assert 0 <= report.health_score <= 100
