from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from day2_models import Telemetry
from diagnosis import Diagnosis


@dataclass(frozen=True)
class FixPlan:
    description: str
    new_pool_max: int
    risk: str

    @classmethod
    def from_diagnosis(cls, diagnosis: Diagnosis) -> "FixPlan":
        return cls(
            description="Increase the simulated database pool size from 20 to 30.",
            new_pool_max=30,
            risk=diagnosis.risk,
        )


@dataclass(frozen=True)
class RemediationResult:
    applied: bool
    db_pool_max_before: int
    db_pool_max_after: int
    action_taken: str


@dataclass(frozen=True)
class AuditRecord:
    diagnosis: str
    recommendation: str
    human_approval: bool
    action_taken: str


def request_approval(input_fn: Callable[[str], str] | None = None) -> bool:
    input_fn = input_fn or input
    print("Apply this fix? [yes/no]: ", end="")
    answer = input_fn("").strip().lower()
    return answer in {"yes", "y"}


def apply_fix(telemetry: Telemetry, fix: FixPlan, approved: bool) -> RemediationResult:
    before = telemetry.db_pool_max
    if not approved:
        return RemediationResult(
            applied=False,
            db_pool_max_before=before,
            db_pool_max_after=before,
            action_taken="fix rejected; no changes made",
        )
    return RemediationResult(
        applied=True,
        db_pool_max_before=before,
        db_pool_max_after=fix.new_pool_max,
        action_taken=f"pool size changed to {fix.new_pool_max}",
    )


def write_audit_record(path: Path, record: AuditRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(record), indent=2) + "\n")
