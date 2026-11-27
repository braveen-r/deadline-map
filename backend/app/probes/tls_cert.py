from __future__ import annotations

from datetime import date, datetime, timezone
import socket
import ssl
from typing import Callable

from app.inventory.models import ResourceSpec, ThresholdConfig
from app.probes.models import ProbeResult, classify_days


CertFetcher = Callable[[str, int, float], dict]


def default_cert_fetcher(host: str, port: int, timeout: float) -> dict:
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls_sock:
            return tls_sock.getpeercert()


def _parse_ssl_expiry(cert: dict) -> date:
    not_after = cert.get("notAfter")
    if not not_after:
        raise ValueError("Certificate missing 'notAfter' field")
    dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    return dt.date()


def probe_tls_cert(
    resource: ResourceSpec,
    thresholds: ThresholdConfig,
    today: date | None = None,
    timeout: float = 5.0,
    fetcher: CertFetcher = default_cert_fetcher,
) -> ProbeResult:
    reference_date = today or date.today()
    host = resource.target or ""
    try:
        cert = fetcher(host, resource.port, timeout)
        expiry_date = _parse_ssl_expiry(cert)
        days_left = (expiry_date - reference_date).days
        status = classify_days(days_left, thresholds.warning_days, thresholds.critical_days)
        return ProbeResult(
            resource_id=resource.id,
            kind=resource.kind,
            expires_on=expiry_date,
            days_remaining=days_left,
            status=status,
            detail=f"TLS cert for {host}:{resource.port} expires {expiry_date.isoformat()}",
        )
    except Exception as exc:
        return ProbeResult(
            resource_id=resource.id,
            kind=resource.kind,
            status="error",
            detail=f"TLS probe failed for {host}:{resource.port}: {exc}",
        )
