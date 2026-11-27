from pathlib import Path
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_status_and_metrics_endpoints():
    example_yaml = Path(__file__).resolve().parents[2] / "examples" / "deadlines.yml"
    client = TestClient(create_app(inventory_path=example_yaml, default_offline=True))

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    status_resp = client.get("/api/status?window=14")
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["services_at_risk_count"] == 1
    assert len(body["impacts"]) == 5

    metrics_resp = client.get("/metrics?window=14")
    assert metrics_resp.status_code == 200
    assert "deadline_map_services_at_risk" in metrics_resp.text
