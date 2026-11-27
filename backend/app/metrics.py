from __future__ import annotations

from app.graph.blast_radius import BlastRadiusReport


def render_prometheus_metrics(report: BlastRadiusReport) -> str:
    lines: list[str] = [
        "# HELP deadline_map_services_at_risk Services impacted by deadlines within the lookahead window.",
        "# TYPE deadline_map_services_at_risk gauge",
        f'deadline_map_services_at_risk{{window_days="{report.window_days}"}} {report.services_at_risk_count}',
        "# HELP deadline_map_deadlines_in_window Deadlines expiring within the lookahead window.",
        "# TYPE deadline_map_deadlines_in_window gauge",
        f'deadline_map_deadlines_in_window{{window_days="{report.window_days}"}} {report.deadlines_in_window_count}',
        "# HELP deadline_map_days_remaining Days remaining until deadline (-1 if unknown).",
        "# TYPE deadline_map_days_remaining gauge",
        "# HELP deadline_map_priority_score Computed blast-radius priority score per resource.",
        "# TYPE deadline_map_priority_score gauge",
    ]

    for item in report.impacts:
        days_val = item.days_remaining if item.days_remaining is not None else -1
        labels = f'resource_id="{item.resource_id}",kind="{item.kind}",status="{item.status}",owner="{item.owner}"'
        lines.append(f"deadline_map_days_remaining{{{labels}}} {days_val}")
        lines.append(f"deadline_map_priority_score{{{labels}}} {item.priority_score}")

    return "\n".join(lines) + "\n"
