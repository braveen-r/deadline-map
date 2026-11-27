from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional
import typer
import uvicorn

from app.graph.blast_radius import compute_blast_radius, evaluate_manual_resource
from app.history.store import SnapshotStore
from app.inventory.loader import load_inventory_from_text
from app.alerts.config import alert_config_from_env
from app.alerts.notifier import dispatch_report_alerts
from app.metrics import render_prometheus_metrics
from app.probes.domain_rdap import probe_domain
from app.probes.models import ProbeResult
from app.probes.runtime_eol import probe_runtime_eol
from app.probes.tls_cert import probe_tls_cert


app = typer.Typer(
    name="deadline-map",
    help="Map expiring infrastructure deadlines to affected services.",
    no_args_is_help=True,
)


def run_checks(
    inventory_path: Path,
    today: date | None = None,
    window_days: int = 14,
    offline: bool = False,
):
    ref_date = today or date.today()
    inventory = load_inventory_from_text(inventory_path.read_text(encoding="utf-8"))
    results: dict[str, ProbeResult] = {}

    for res in inventory.resources:
        if res.kind in {"token", "trial"}:
            results[res.id] = evaluate_manual_resource(res, inventory.thresholds, ref_date)
        elif offline:
            results[res.id] = ProbeResult(
                resource_id=res.id,
                kind=res.kind,
                expires_on=None,
                days_remaining=None,
                status="ok",
                detail="Skipped live probe (--offline)",
            )
        elif res.kind == "tls_cert":
            results[res.id] = probe_tls_cert(res, inventory.thresholds, today=ref_date)
        elif res.kind == "domain":
            results[res.id] = probe_domain(res, inventory.thresholds, today=ref_date)
        elif res.kind == "runtime":
            results[res.id] = probe_runtime_eol(res, inventory.thresholds, today=ref_date)

    return compute_blast_radius(inventory, results, today=ref_date, window_days=window_days)


def status_cmd(
    file: Path = typer.Option(
        Path("examples/deadlines.yml"),
        "--file",
        "-f",
        help="Path to deadlines inventory YAML file.",
    ),
    window: int = typer.Option(14, "--window", "-w", help="Blast radius lookahead in days."),
    offline: bool = typer.Option(
        False,
        "--offline",
        help="Skip live network probes and evaluate manual deadlines only.",
    ),
    db: Optional[Path] = typer.Option(
        None,
        "--db",
        help="Optional DuckDB file path to record snapshot history.",
    ),
    metrics_out: Optional[Path] = typer.Option(
        None,
        "--metrics-out",
        help="Optional file path to write Prometheus textfile metrics.",
    ),
    alert: bool = typer.Option(
        False,
        "--alert",
        help="Dispatch alerts using environment variables or .env configuration.",
    ),
    env_file: Path = typer.Option(
        Path(".env"),
        "--env-file",
        help="Path to .env file for alert credentials.",
    ),
) -> None:
    """Show deadline status and service blast radius."""
    report = run_checks(file, window_days=window, offline=offline)

    if db is not None:
        store = SnapshotStore(db)
        store.record_report(report)

    if metrics_out is not None:
        metrics_out.parent.mkdir(parents=True, exist_ok=True)
        metrics_out.write_text(render_prometheus_metrics(report), encoding="utf-8")

    typer.echo(f"{'DEADLINE':<26} {'IN':<10} {'STATUS':<10} {'BREAKS'}")
    typer.echo("-" * 80)

    for item in report.impacts:
        in_str = f"{item.days_remaining}d" if item.days_remaining is not None else "n/a"
        breaks_str = (
            ", ".join(f"{s.service_name} ({s.impact})" for s in item.affected_services)
            if item.affected_services
            else "-"
        )
        typer.echo(f"{item.resource_id:<26} {in_str:<10} {item.status.upper():<10} {breaks_str}")

    typer.echo("")
    typer.echo(
        f"Blast radius ({report.window_days}d): {report.services_at_risk_count} service(s) "
        f"affected by {report.deadlines_in_window_count} deadline(s)."
    )

    if alert:
        sent = dispatch_report_alerts(report, **alert_config_from_env(env_file))
        channels = ", ".join(sent) if sent else "none"
        typer.echo(f"Alerts dispatched: {len(sent)} ({channels})")


def serve_cmd(
    file: Path = typer.Option(
        Path("examples/deadlines.yml"),
        "--file",
        "-f",
        help="Path to deadlines inventory YAML file.",
    ),
    db: Optional[Path] = typer.Option(
        None,
        "--db",
        help="Optional DuckDB file path for /api/history.",
    ),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind host."),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port."),
) -> None:
    """Start the FastAPI server for deadline-map."""
    from app.main import create_app

    fastapi_app = create_app(inventory_path=file, db_path=db, default_offline=True)
    uvicorn.run(fastapi_app, host=host, port=port)


def version_cmd() -> None:
    """Print the deadline-map CLI version."""
    typer.echo("deadline-map v0.1.0")


app.command(name="status")(status_cmd)
app.command(name="serve")(serve_cmd)
app.command(name="version")(version_cmd)


if __name__ == "__main__":
    app()
