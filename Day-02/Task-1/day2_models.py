from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


@dataclass(frozen=True)
class Telemetry:
    service: str
    baseline_p95_latency_seconds: float
    current_p95_latency_seconds: float
    db_pool_max: int
    db_pool_in_use: int
    db_waiting_requests: int
    logs: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Telemetry":
        try:
            baseline = data["baseline"]
            current = data["current"]
            telemetry = cls(
                service=str(data["service"]),
                baseline_p95_latency_seconds=float(baseline["p95_latency_seconds"]),
                current_p95_latency_seconds=float(current["p95_latency_seconds"]),
                db_pool_max=int(current["db_pool_max"]),
                db_pool_in_use=int(current["db_pool_in_use"]),
                db_waiting_requests=int(current["db_waiting_requests"]),
                logs=data.get("logs", []),
            )
        except KeyError as exc:
            raise ValueError(f"missing telemetry field: {exc.args[0]}") from exc
        except (TypeError, ValueError) as exc:
            raise ValueError("telemetry fields must contain valid numeric values") from exc

        telemetry.validate()
        return telemetry

    def validate(self) -> None:
        if self.baseline_p95_latency_seconds <= 0:
            raise ValueError("baseline_p95_latency_seconds must be positive")
        if not math.isfinite(self.baseline_p95_latency_seconds) or not math.isfinite(self.current_p95_latency_seconds):
            raise ValueError("latency values must be finite")
        if self.current_p95_latency_seconds < 0:
            raise ValueError("current_p95_latency_seconds cannot be negative")
        if self.db_pool_max <= 0:
            raise ValueError("db_pool_max must be positive")
        if self.db_pool_in_use < 0 or self.db_pool_in_use > self.db_pool_max:
            raise ValueError("db_pool_in_use must be between zero and db_pool_max")
        if self.db_waiting_requests < 0:
            raise ValueError("db_waiting_requests cannot be negative")
        if not isinstance(self.logs, list) or not all(isinstance(item, str) for item in self.logs):
            raise ValueError("logs must be a list of strings")


@dataclass(frozen=True)
class Evidence:
    telemetry: Telemetry

    @classmethod
    def from_telemetry(cls, telemetry: Telemetry) -> "Evidence":
        telemetry.validate()
        return cls(telemetry=telemetry)

    def latency_multiplier(self) -> float:
        return self.telemetry.current_p95_latency_seconds / self.telemetry.baseline_p95_latency_seconds

    def pool_saturation(self) -> float:
        return self.telemetry.db_pool_in_use / self.telemetry.db_pool_max
