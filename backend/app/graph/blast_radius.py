from __future__ import annotations

from datetime import date
from typing import Literal
from pydantic import BaseModel

from app.inventory.models import Criticality, Inventory, ResourceSpec
from app.probes.models import ProbeResult, ProbeStatus, classify_days


SeverityLevel = Literal["low", "medium", "high", "critical"]

_CRITICALITY_WEIGHT: dict[Criticality, int] = {
    "low": 1,
    "medium": 2,
    "high": 4,
}

_STATUS_RANK: dict[ProbeStatus, int] = {
    "expired": 4,
    "critical": 3,
    "warning": 2,
    "error": 1,
    "ok": 0,
}

_DEFAULT_RENEWAL_HINTS: dict[str, str] = {
    "tls_cert": "Renew TLS certificate and reload ingress/reverse proxy",
    "domain": "Renew domain registration before registrar grace period ends",
    "runtime": "Upgrade runtime/base image to a supported release cycle",
    "token": "Rotate token/credential and update secrets without storing secrets in inventory",
    "trial": "Migrate workload or select an approved plan before trial expiration",
}


class AffectedService(BaseModel):
    service_name: str
    criticality: Criticality
    impact: str


class DeadlineImpact(BaseModel):
    resource_id: str
    kind: str
    owner: str
    status: ProbeStatus
    severity: SeverityLevel
    days_remaining: int | None
    expires_on: date | None
    detail: str
    renewal_hint: str
    priority_score: int
    affected_services: list[AffectedService]


class CategoryHealth(BaseModel):
    category: str
    label: str
    total: int
    issues: int
    state: str


class BlastRadiusReport(BaseModel):
    as_of: date
    window_days: int
    health_score: int
    health_formula: str
    health_breakdown: list[CategoryHealth]
    impacts: list[DeadlineImpact]
    services_at_risk_count: int
    deadlines_in_window_count: int


def evaluate_manual_resource(
    resource: ResourceSpec,
    thresholds,
    today: date,
) -> ProbeResult:
    expiry = resource.resolved_manual_expiry()
    if expiry is None:
        return ProbeResult(
            resource_id=resource.id,
            kind=resource.kind,
            status="error",
            detail=f"Resource '{resource.id}' has no resolved expiry date",
        )
    days_left = (expiry - today).days
    status = classify_days(days_left, thresholds.warning_days, thresholds.critical_days)
    return ProbeResult(
        resource_id=resource.id,
        kind=resource.kind,
        expires_on=expiry,
        days_remaining=days_left,
        status=status,
        detail=f"{resource.kind} '{resource.id}' expires {expiry.isoformat()}",
    )


def _compute_severity(status: ProbeStatus, affected: list[AffectedService]) -> SeverityLevel:
    has_high = any(s.criticality == "high" for s in affected)
    if status == "expired" or (status == "critical" and (has_high or len(affected) >= 2)):
        return "critical"
    if status in {"critical", "error"} or (status == "warning" and (has_high or len(affected) >= 2)):
        return "high"
    if status == "warning" or len(affected) > 0:
        return "medium"
    return "low"


def _build_health_summary(impacts: list[DeadlineImpact]) -> tuple[int, str, list[CategoryHealth]]:
    if not impacts:
        return 100, "100 - penalties (no resources)", []

    penalty = 0
    cat_stats: dict[str, tuple[str, int, int]] = {
        "tls_cert": ("Certificates", 0, 0),
        "domain": ("Domains", 0, 0),
        "token": ("Tokens & Trials", 0, 0),
        "runtime": ("Runtimes", 0, 0),
    }

    for item in impacts:
        if item.status == "expired":
            penalty += 25
        elif item.status == "critical":
            penalty += 15
        elif item.status == "warning":
            penalty += 7
        elif item.status == "error":
            penalty += 10

        cat_key = "token" if item.kind in {"token", "trial"} else item.kind
        label, total, issues = cat_stats.get(cat_key, (cat_key, 0, 0))
        is_issue = 1 if item.status != "ok" else 0
        cat_stats[cat_key] = (label, total + 1, issues + is_issue)

    score = max(0, min(100, 100 - penalty))
    breakdown: list[CategoryHealth] = []
    for key, (label, total, issues) in cat_stats.items():
        if total == 0:
            continue
        state = "Healthy" if issues == 0 else ("Needs attention" if score >= 60 else "At risk")
        breakdown.append(CategoryHealth(category=key, label=label, total=total, issues=issues, state=state))

    formula = "100 - (25*expired + 15*critical + 10*error + 7*warning), clamped 0..100"
    return score, formula, breakdown


def compute_blast_radius(
    inventory: Inventory,
    probe_results: dict[str, ProbeResult],
    today: date,
    window_days: int = 14,
) -> BlastRadiusReport:
    deps_by_resource: dict[str, list[AffectedService]] = {
        r.id: [] for r in inventory.resources
    }
    for svc in inventory.services:
        for dep in svc.depends_on:
            deps_by_resource.setdefault(dep.resource, []).append(
                AffectedService(
                    service_name=svc.name,
                    criticality=svc.criticality,
                    impact=dep.impact,
                )
            )

    impacts: list[DeadlineImpact] = []
    at_risk_services: set[str] = set()
    deadlines_in_window = 0

    for res in inventory.resources:
        result = probe_results[res.id]
        affected = deps_by_resource.get(res.id, [])

        urgency_bonus = 0
        if result.status == "expired":
            urgency_bonus = 100
        elif result.status == "critical":
            urgency_bonus = 70
        elif result.status == "warning":
            urgency_bonus = 40
        elif result.status == "error":
            urgency_bonus = 25

        service_weight = sum(_CRITICALITY_WEIGHT[s.criticality] for s in affected)
        priority_score = urgency_bonus + (service_weight * 10)
        severity = _compute_severity(result.status, affected)
        hint = res.renewal_hint.strip() or _DEFAULT_RENEWAL_HINTS.get(res.kind, "Review and renew before expiry")

        if result.days_remaining is not None and result.days_remaining <= window_days:
            deadlines_in_window += 1
            for svc in affected:
                at_risk_services.add(svc.service_name)

        impacts.append(
            DeadlineImpact(
                resource_id=res.id,
                kind=res.kind,
                owner=res.owner,
                status=result.status,
                severity=severity,
                days_remaining=result.days_remaining,
                expires_on=result.expires_on,
                detail=result.detail,
                renewal_hint=hint,
                priority_score=priority_score,
                affected_services=affected,
            )
        )

    impacts.sort(
        key=lambda item: (
            -_STATUS_RANK[item.status],
            -item.priority_score,
            item.days_remaining if item.days_remaining is not None else 999999,
        )
    )

    health_score, health_formula, health_breakdown = _build_health_summary(impacts)

    return BlastRadiusReport(
        as_of=today,
        window_days=window_days,
        health_score=health_score,
        health_formula=health_formula,
        health_breakdown=health_breakdown,
        impacts=impacts,
        services_at_risk_count=len(at_risk_services),
        deadlines_in_window_count=deadlines_in_window,
    )
