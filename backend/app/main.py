from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.cli import run_checks
from app.history.store import SnapshotStore
from app.metrics import render_prometheus_metrics


def create_app(
    inventory_path: Path = Path("examples/deadlines.yml"),
    db_path: Path | None = None,
    default_offline: bool = True,
) -> FastAPI:
    app = FastAPI(
        title="deadline-map",
        version="0.1.0",
        description="Dependency-aware infrastructure deadline and blast-radius API.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    repo_root = Path(__file__).resolve().parents[2]
    dist_dir = repo_root / "frontend" / "dist"
    dist_assets = dist_dir / "assets"
    dist_index = dist_dir / "index.html"

    if dist_assets.exists():
        app.mount("/assets", StaticFiles(directory=str(dist_assets)), name="assets")

    @app.get("/")
    def root():
        if dist_index.exists():
            return FileResponse(dist_index)
        return {
            "service": "deadline-map",
            "version": "0.1.0",
            "endpoints": ["/health", "/api/status", "/api/history", "/metrics", "/docs"],
        }

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/status")
    def get_status(
        window: int = Query(default=14, ge=1, le=365),
        offline: bool = Query(default=default_offline),
    ):
        if not inventory_path.exists():
            raise HTTPException(status_code=404, detail=f"Inventory not found: {inventory_path}")
        return run_checks(inventory_path, window_days=window, offline=offline)

    @app.get("/metrics", response_class=PlainTextResponse)
    def get_metrics(
        window: int = Query(default=14, ge=1, le=365),
        offline: bool = Query(default=default_offline),
    ) -> str:
        if not inventory_path.exists():
            raise HTTPException(status_code=404, detail=f"Inventory not found: {inventory_path}")
        report = run_checks(inventory_path, window_days=window, offline=offline)
        return render_prometheus_metrics(report)

    @app.get("/api/history")
    def get_history(limit: int = Query(default=50, ge=1, le=500)):
        if db_path is None or not db_path.exists():
            return {"count": 0, "items": []}
        store = SnapshotStore(db_path)
        with store._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    recorded_at,
                    as_of,
                    resource_id,
                    kind,
                    status,
                    days_remaining,
                    priority_score,
                    affected_services_count
                FROM deadline_snapshots
                ORDER BY recorded_at DESC
                LIMIT ?
                """,
                [limit],
            ).fetchall()
        columns = [
            "recorded_at",
            "as_of",
            "resource_id",
            "kind",
            "status",
            "days_remaining",
            "priority_score",
            "affected_services_count",
        ]
        items = [dict(zip(columns, row)) for row in rows]
        return {"count": len(items), "items": items}

    return app


app = create_app()
