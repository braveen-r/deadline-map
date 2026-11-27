from datetime import date

from app.inventory.models import ResourceSpec, ThresholdConfig
from app.probes.domain_rdap import probe_domain
from app.probes.runtime_eol import probe_runtime_eol
from app.probes.tls_cert import probe_tls_cert


def test_tls_probe_critical_threshold():
    res = ResourceSpec(id="cert-test", kind="tls_cert", target="example.com", port=443)
    thresholds = ThresholdConfig(warning_days=30, critical_days=7)
    fake_cert = {"notAfter": "Dec 02 00:00:00 2026 GMT"}

    result = probe_tls_cert(
        res,
        thresholds,
        today=date(2026, 11, 27),
        fetcher=lambda host, port, timeout: fake_cert,
    )
    assert result.status == "critical"
    assert result.days_remaining == 5
    assert result.expires_on == date(2026, 12, 2)


def test_domain_rdap_probe_healthy():
    res = ResourceSpec(id="dom-test", kind="domain", target="example.com")
    thresholds = ThresholdConfig(warning_days=30, critical_days=7)
    fake_rdap = {"events": [{"eventAction": "expiration", "eventDate": "2027-09-23T00:00:00Z"}]}

    result = probe_domain(
        res,
        thresholds,
        today=date(2026, 11, 27),
        fetcher=lambda domain, timeout: fake_rdap,
    )
    assert result.status == "ok"
    assert result.days_remaining == 300


def test_runtime_eol_probe_expired():
    res = ResourceSpec(id="node-18", kind="runtime", product="nodejs", cycle="18")
    thresholds = ThresholdConfig(warning_days=30, critical_days=7)
    fake_eol = {"eol": "2025-04-30"}

    result = probe_runtime_eol(
        res,
        thresholds,
        today=date(2026, 11, 27),
        fetcher=lambda product, cycle, timeout: fake_eol,
    )
    assert result.status == "expired"
    assert result.days_remaining is not None and result.days_remaining < 0
