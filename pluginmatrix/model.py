from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


STATES = (
    "ENVIRONMENT_INVALID",
    "SERVER_START_FAILED",
    "SERVER_START_TIMEOUT",
    "PLUGIN_NOT_DISCOVERED",
    "PLUGIN_LOAD_FAILED",
    "PLUGIN_ENABLE_FAILED",
    "PLUGIN_DISABLED",
    "PLUGIN_UNSUPPORTED",
    "CANCELLED",
    "PASS",
    "UNKNOWN_FAILURE",
)


@dataclass
class Check:
    name: str
    status: str
    detail: str | None = None


@dataclass
class EvidenceEvent:
    kind: str
    timestamp: float
    source: str = "log"
    detail: str | None = None


@dataclass
class VerificationResult:
    result: str = "UNKNOWN_FAILURE"
    failure_stage: str | None = None
    reason: str | None = None
    checks: list[Check] = field(default_factory=list)
    evidence: list[EvidenceEvent] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    report_path: str | None = None
    log_path: str | None = None
    workdir: str | None = None
    behavior: dict[str, Any] = field(default_factory=lambda: {
        'schema': 1, 'verdict': 'NOT_RUN', 'reason': None, 'plan': None,
        'plan_sha256': None, 'checks': [], 'post_health': {'status': 'NOT_RUN'}})

    @property
    def passed(self) -> bool:
        from .behavior import verification_passed
        return verification_passed(self.result, self.behavior)

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "runtime_verdict": self.result,
            "verification_passed": self.passed,
            "checks": [asdict(check) for check in self.checks],
            "evidence": [asdict(event) for event in self.evidence],
        }
