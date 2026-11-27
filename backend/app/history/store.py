from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import duckdb

from app.graph.blast_radius import BlastRadiusReport


class SnapshotStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.db_path))

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS deadline_snapshots (
                    recorded_at TIMESTAMPTZ NOT NULL,
                    as_of DATE NOT NULL,
                    resource_id VARCHAR NOT NULL,
                    kind VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    days_remaining INTEGER,
                    priority_score INTEGER NOT NULL,
                    affected_services_count INTEGER NOT NULL
                )
                """
            )

    def record_report(
        self,
        report: BlastRadiusReport,
        recorded_at: datetime | None = None,
    ) -> int:
        ts = recorded_at or datetime.now(timezone.utc)
        rows = [
            (
                ts,
                report.as_of,
                item.resource_id,
                item.kind,
                item.status,
                item.days_remaining,
                item.priority_score,
                len(item.affected_services),
            )
            for item in report.impacts
        ]
        if not rows:
            return 0
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO deadline_snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        return len(rows)

    def count_snapshots(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM deadline_snapshots").fetchone()
        return int(row[0]) if row else 0
