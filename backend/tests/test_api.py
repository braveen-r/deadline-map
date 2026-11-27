from pathlib import Path
from fastapi.testclient import TestClient

from app.cli import run_checks
from app.history.store import SnapshotStore
from app.main import create_app


def test_root_and_history_endpoints(tmp_path: Path):
    inv = Path("examples/deadlines.yml")
    db_path = tmp_path / "snapshots.duckdb"
    app = create_app(inventory_path=inv, db_path=db_path, default_offline=True)
    client = TestClient(app)

    root_resp = client.get("/")
    assert root_resp.status_code == 200

    empty_hist = client.get("/api/history?limit=10")
    assert empty_hist.status_code == 200
    assert empty_hist.json() == {"count": 0, "items": []}

    report = run_checks(inv, window_days=14, offline=True)
    store = SnapshotStore(db_path)
    store.record_report(report)

    populated_hist = client.get("/api/history?limit=10")
    assert populated_hist.status_code == 200
    payload = populated_hist.json()
    assert payload["count"] == len(report.impacts)
    assert len(payload["items"]) == len(report.impacts)


def test_health_status_and_metrics_endpoints():
    inv = Path("examples/deadlines.yml")
    app = create_app(inventory_path=inv, default_offline=True)
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    status = client.get("/api/status?window=14&offline=true")
    assert status.status_code == 200
    body = status.json()
    assert body["window_days"] == 14
    assert len(body["impacts"]) >= 1

    metrics = client.get("/metrics?window=14&offline=true")
    assert metrics.status_code == 200
    assert "deadline_map_services_at_risk" in metrics.text
