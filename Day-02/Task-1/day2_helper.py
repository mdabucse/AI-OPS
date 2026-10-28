from __future__ import annotations

import argparse
import json
from pathlib import Path

from day2_models import Evidence, Telemetry
from diagnosis import ModelClient, OllamaClient
from remediation import AuditRecord, FixPlan, apply_fix, request_approval, write_audit_record


def _record_failure(audit_path: Path, reason: str) -> None:
    try:
        write_audit_record(
            audit_path,
            AuditRecord(
                diagnosis="not available",
                recommendation="not available",
                human_approval=False,
                action_taken=f"not attempted: {reason}",
            ),
        )
    except OSError:
        pass


def run(input_path: Path, audit_path: Path, model_client: ModelClient) -> int:
    try:
        data = json.loads(input_path.read_text())
        telemetry = Telemetry.from_dict(data)
        evidence = Evidence.from_telemetry(telemetry)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: invalid scenario: {exc}")
        _record_failure(audit_path, f"invalid scenario ({exc})")
        return 2

    print(
        f"Login P95 latency: {telemetry.current_p95_latency_seconds:.2f}s "
        f"(baseline {telemetry.baseline_p95_latency_seconds:.2f}s; "
        f"{evidence.latency_multiplier():.2f}x baseline)"
    )
    try:
        diagnosis = model_client.diagnose(evidence)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"ERROR: diagnosis unavailable: {exc}")
        _record_failure(audit_path, f"diagnosis unavailable ({exc})")
        return 3

    print(f"\nUser impact: {diagnosis.user_impact}")
    print(f"Root cause: {diagnosis.root_cause}")
    print("Evidence:")
    for item in diagnosis.evidence:
        print(f"- {item}")
    print(f"Recommended fix: {diagnosis.recommended_fix}")
    print(f"Risk: {diagnosis.risk}")
    print(f"Confidence: {diagnosis.confidence:.0%}")

    fix = FixPlan.from_diagnosis(diagnosis)
    print(f"Planned action: {fix.description}")
    approved = request_approval()
    result = apply_fix(telemetry, fix, approved=approved)

    if result.applied:
        data["current"]["db_pool_max"] = result.db_pool_max_after
        input_path.write_text(json.dumps(data, indent=2) + "\n")
        print("Fix approved and applied.")
    else:
        print("Fix rejected. No changes were made.")

    write_audit_record(
        audit_path,
        AuditRecord(
            diagnosis=diagnosis.root_cause,
            recommendation=fix.description,
            human_approval=approved,
            action_taken=result.action_taken,
        ),
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Day 2 AIOps login incident helper")
    parser.add_argument("--scenario", type=Path, default=Path("scenario.json"))
    parser.add_argument("--audit", type=Path, default=Path("decision_log.json"))
    args = parser.parse_args()
    return run(args.scenario, args.audit, OllamaClient())


if __name__ == "__main__":
    raise SystemExit(main())
