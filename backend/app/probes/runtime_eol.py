from __future__ import annotations

from datetime import date
from typing import Callable
import httpx

from app.inventory.models import ResourceSpec, ThresholdConfig
from app.probes.models import ProbeResult, classify_days


EolFetcher = Callable[[str, str, float], dict]


def default_eol_fetcher(product: str, cycle: str, timeout: float) -> dict:
    url = f"https://endoflife.date/api/{product}/{cycle}.json"
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()


def _extract_eol_date(payload: dict) -> date | None:
    eol_val = payload.get("eol")
    if isinstance(eol_val, str) and eol_val:
        return date.fromisoformat(eol_val[:10])
    return None


def probe_runtime_eol(
    resource: ResourceSpec,
    thresholds: ThresholdConfig,
    today: date | None = None,
    timeout: float = 8.0,
    fetcher: EolFetcher = default_eol_fetcher,
) -> ProbeResult:
    reference_date = today or date.today()
    product = resource.product or ""
    cycle = resource.cycle or ""
    try:
        payload = fetcher(product, cycle, timeout)
        eol_date = _extract_eol_date(payload)
        if eol_date is None:
            return ProbeResult(
                resource_id=resource.id,
                kind=resource.kind,
                expires_on=None,
                days_remaining=None,
                status="ok",
                detail=f"Runtime {product} {cycle} has no scheduled EOL date",
            )
        days_left = (eol_date - reference_date).days
        status = classify_days(days_left, thresholds.warning_days, thresholds.critical_days)
        return ProbeResult(
            resource_id=resource.id,
            kind=resource.kind,
            expires_on=eol_date,
            days_remaining=days_left,
            status=status,
            detail=f"Runtime {product} {cycle} EOL on {eol_date.isoformat()}",
        )
    except Exception as exc:
        return ProbeResult(
            resource_id=resource.id,
            kind=resource.kind,
            status="error",
            detail=f"EOL lookup failed for {product} {cycle}: {exc}",
        )
