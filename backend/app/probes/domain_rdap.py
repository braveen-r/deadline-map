from __future__ import annotations

from datetime import date, datetime
from typing import Callable
import httpx

from app.inventory.models import ResourceSpec, ThresholdConfig
from app.probes.models import ProbeResult, classify_days


RdapFetcher = Callable[[str, float], dict]


def default_rdap_fetcher(domain: str, timeout: float) -> dict:
    url = f"https://rdap.org/domain/{domain}"
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()


def _extract_rdap_expiration(payload: dict) -> date:
    for event in payload.get("events", []):
        if event.get("eventAction") == "expiration" and event.get("eventDate"):
            raw = str(event["eventDate"])
            # Handle ISO timestamps like "2027-05-10T00:00:00Z" or date strings
            if "T" in raw:
                return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
            return date.fromisoformat(raw[:10])
    raise ValueError("No expiration event found in RDAP response")


def probe_domain(
    resource: ResourceSpec,
    thresholds: ThresholdConfig,
    today: date | None = None,
    timeout: float = 8.0,
    fetcher: RdapFetcher = default_rdap_fetcher,
) -> ProbeResult:
    reference_date = today or date.today()
    domain = resource.target or ""
    try:
        payload = fetcher(domain, timeout)
        expiry_date = _extract_rdap_expiration(payload)
        days_left = (expiry_date - reference_date).days
        status = classify_days(days_left, thresholds.warning_days, thresholds.critical_days)
        return ProbeResult(
            resource_id=resource.id,
            kind=resource.kind,
            expires_on=expiry_date,
            days_remaining=days_left,
            status=status,
            detail=f"Domain {domain} expires {expiry_date.isoformat()}",
        )
    except Exception as exc:
        return ProbeResult(
            resource_id=resource.id,
            kind=resource.kind,
            status="error",
            detail=f"RDAP lookup failed for {domain}: {exc}",
        )
