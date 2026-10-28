from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol
from urllib import error, request

from day2_models import Evidence


@dataclass(frozen=True)
class Diagnosis:
    user_impact: str
    root_cause: str
    evidence: list[str]
    recommended_fix: str
    risk: str
    confidence: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Diagnosis":
        if not isinstance(data, dict):
            raise ValueError("diagnosis must be a JSON object")
        required = (
            "user_impact",
            "root_cause",
            "evidence",
            "recommended_fix",
            "risk",
            "confidence",
        )
        missing = [field for field in required if field not in data]
        if missing:
            raise ValueError(f"missing diagnosis field: {missing[0]}")
        if not isinstance(data["evidence"], list) or not all(isinstance(item, str) for item in data["evidence"]):
            raise ValueError("evidence must be a list of strings")
        for field in ("user_impact", "root_cause", "recommended_fix", "risk"):
            if not isinstance(data[field], str) or not data[field].strip():
                raise ValueError(f"{field} must be a non-empty string")
        try:
            confidence = float(data["confidence"])
        except (TypeError, ValueError) as exc:
            raise ValueError("confidence must be numeric") from exc
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return cls(
            user_impact=str(data["user_impact"]),
            root_cause=str(data["root_cause"]),
            evidence=data["evidence"],
            recommended_fix=str(data["recommended_fix"]),
            risk=str(data["risk"]),
            confidence=confidence,
        )


class ModelClient(Protocol):
    def diagnose(self, evidence: Evidence) -> Diagnosis:
        ...


def build_prompt(evidence: Evidence) -> str:
    telemetry = evidence.telemetry
    logs = "\n".join(f"- {line}" for line in telemetry.logs)
    return f"""You are an AIOps incident assistant.

Analyze the following login-service evidence and return JSON only.

Telemetry:
- Service: {telemetry.service}
- Normal P95 latency: {telemetry.baseline_p95_latency_seconds} seconds
- Current P95 latency: {telemetry.current_p95_latency_seconds} seconds
- Database pool maximum: {telemetry.db_pool_max}
- Database connections in use: {telemetry.db_pool_in_use}
- Waiting requests: {telemetry.db_waiting_requests}
- Latency multiplier: {evidence.latency_multiplier():.2f}
- Pool saturation: {evidence.pool_saturation():.2f}

Logs:
{logs}

Return a JSON object with exactly these fields:
{{
  "user_impact": "...",
  "root_cause": "...",
  "evidence": ["..."],
  "recommended_fix": "...",
  "risk": "...",
  "confidence": 0.0
}}
"""


class OllamaClient:
    def __init__(self, model: str | None = None, base_url: str | None = None, timeout: float = 30.0):
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen3:8b")
        self.base_url = (base_url or os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.timeout = timeout

    def diagnose(self, evidence: Evidence) -> Diagnosis:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [{"role": "user", "content": build_prompt(evidence)}],
        }
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Ollama diagnosis failed: {exc}") from exc

        try:
            content = result["message"]["content"]
            diagnosis_data = json.loads(content)
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Ollama returned invalid diagnosis JSON") from exc
        return Diagnosis.from_dict(diagnosis_data)


class FakeModelClient:
    def diagnose(self, evidence: Evidence) -> Diagnosis:
        telemetry = evidence.telemetry
        return Diagnosis.from_dict({
            "user_impact": f"Login P95 latency increased to {telemetry.current_p95_latency_seconds:.2f} seconds.",
            "root_cause": "The database connection pool is exhausted, so login requests wait in a queue.",
            "evidence": [
                f"P95 latency increased from {telemetry.baseline_p95_latency_seconds:.2f}s to {telemetry.current_p95_latency_seconds:.2f}s.",
                f"The database pool is {evidence.pool_saturation():.0%} utilized with {telemetry.db_waiting_requests} waiting requests.",
                "Logs report that the database connection pool is exhausted.",
            ],
            "recommended_fix": "Increase the simulated database pool size from 20 to 30.",
            "risk": "A larger pool may increase database concurrency and resource usage.",
            "confidence": 0.98,
        })
