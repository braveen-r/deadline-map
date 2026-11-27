from datetime import date
from pathlib import Path
import pytest
from pydantic import ValidationError

from app.inventory.models import load_inventory_from_text


def test_example_inventory_loads_cleanly():
    example_path = Path(__file__).resolve().parents[2] / "examples" / "deadlines.yml"
    inv = load_inventory_from_text(example_path.read_text(encoding="utf-8"))

    assert len(inv.resources) == 5
    assert len(inv.services) == 3

    token = next(r for r in inv.resources if r.id == "token-ghcr-ci")
    assert token.resolved_manual_expiry() == date(2026, 11, 30)


def test_unknown_resource_reference_fails_validation():
    bad_yaml = """
resources:
  - id: domain-main
    kind: domain
    target: example.com
services:
  - name: web-app
    depends_on:
      - resource: cert-does-not-exist
        impact: "HTTPS fails"
"""
    with pytest.raises(ValidationError, match="unknown resource 'cert-does-not-exist'"):
        load_inventory_from_text(bad_yaml)


def test_missing_kind_specific_fields_fails_validation():
    bad_yaml = """
resources:
  - id: broken-runtime
    kind: runtime
    product: nodejs
"""
    with pytest.raises(ValidationError, match="requires 'product' and 'cycle'"):
        load_inventory_from_text(bad_yaml)
