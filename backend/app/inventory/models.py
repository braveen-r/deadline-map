from __future__ import annotations

from datetime import date, timedelta
from typing import Literal
import yaml
from pydantic import BaseModel, Field, model_validator


ResourceKind = Literal["tls_cert", "domain", "runtime", "token", "trial"]
Criticality = Literal["low", "medium", "high"]


class ThresholdConfig(BaseModel):
    warning_days: int = Field(default=30, gt=0)
    critical_days: int = Field(default=7, gt=0)

    @model_validator(mode="after")
    def validate_order(self) -> ThresholdConfig:
        if self.critical_days >= self.warning_days:
            raise ValueError("critical_days must be smaller than warning_days")
        return self


class ResourceSpec(BaseModel):
    id: str = Field(min_length=2)
    kind: ResourceKind
    owner: str = "unassigned"
    renewal_hint: str = ""

    # Probe-specific fields
    target: str | None = None
    port: int = Field(default=443, ge=1, le=65535)
    product: str | None = None
    cycle: str | None = None

    # Manual deadline fields
    expires_on: date | None = None
    rotated_on: date | None = None
    rotation_days: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_kind_fields(self) -> ResourceSpec:
        if self.kind in {"tls_cert", "domain"} and not self.target:
            raise ValueError(f"Resource '{self.id}' ({self.kind}) requires 'target'")
        if self.kind == "runtime" and (not self.product or not self.cycle):
            raise ValueError(f"Resource '{self.id}' (runtime) requires 'product' and 'cycle'")
        if self.kind == "token":
            if self.expires_on is None and (self.rotated_on is None or self.rotation_days is None):
                raise ValueError(
                    f"Resource '{self.id}' (token) requires 'expires_on' or both 'rotated_on' and 'rotation_days'"
                )
        if self.kind == "trial" and self.expires_on is None:
            raise ValueError(f"Resource '{self.id}' (trial) requires 'expires_on'")
        return self

    def resolved_manual_expiry(self) -> date | None:
        if self.expires_on is not None:
            return self.expires_on
        if self.rotated_on is not None and self.rotation_days is not None:
            return self.rotated_on + timedelta(days=self.rotation_days)
        return None


class ServiceDependency(BaseModel):
    resource: str
    impact: str = "Service degradation or outage"


class ServiceSpec(BaseModel):
    name: str = Field(min_length=2)
    criticality: Criticality = "medium"
    depends_on: list[ServiceDependency] = Field(default_factory=list)


class Inventory(BaseModel):
    version: int = 1
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    resources: list[ResourceSpec] = Field(default_factory=list)
    services: list[ServiceSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self) -> Inventory:
        seen_ids: set[str] = set()
        for res in self.resources:
            if res.id in seen_ids:
                raise ValueError(f"Duplicate resource id: '{res.id}'")
            seen_ids.add(res.id)

        seen_services: set[str] = set()
        for svc in self.services:
            if svc.name in seen_services:
                raise ValueError(f"Duplicate service name: '{svc.name}'")
            seen_services.add(svc.name)
            for dep in svc.depends_on:
                if dep.resource not in seen_ids:
                    raise ValueError(
                        f"Service '{svc.name}' references unknown resource '{dep.resource}'"
                    )
        return self


def load_inventory_from_text(raw_yaml: str) -> Inventory:
    data = yaml.safe_load(raw_yaml) or {}
    return Inventory.model_validate(data)
