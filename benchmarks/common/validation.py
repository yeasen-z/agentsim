"""Benchmark independent native pack conformance checks."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from .interfaces import NativeBenchmarkPack


@dataclass(frozen=True)
class ValidationIssue:
    gate: str
    message: str
    case_id: Optional[str] = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate,
            "message": self.message,
            "case_id": self.case_id,
            "details": dict(self.details),
        }


@dataclass
class ValidationReport:
    benchmark_id: str
    claimed_level: str
    checks: dict[str, bool] = field(default_factory=dict)
    issues: list[ValidationIssue] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(self.checks.values()) and not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "claimed_level": self.claimed_level,
            "passed": self.passed,
            "checks": dict(self.checks),
            "counts": dict(self.counts),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def validate_pack(
    pack: NativeBenchmarkPack,
    *,
    selection=None,
    claimed_level: str = "data",
) -> ValidationReport:
    """Validate case identity, suite references, JSON records, and determinism.

    ``data`` is the highest generic level because runnable/ground-truth gates
    require benchmark-specific or agent-specific behavioral expectations.
    """
    info = pack.info()
    report = ValidationReport(benchmark_id=info.benchmark_id, claimed_level=claimed_level)
    if claimed_level not in {"data", "runnable", "ground_truth", "parity", "leaderboard"}:
        report.issues.append(
            ValidationIssue("level", f"Unknown compatibility level: {claimed_level!r}")
        )
        return report
    suites = pack.suites()
    suite_ids = {suite.suite_id for suite in suites}
    report.checks["benchmark_identity"] = bool(info.benchmark_id and info.version)
    report.checks["suite_ids_unique"] = len(suite_ids) == len(suites)
    if not report.checks["suite_ids_unique"]:
        report.issues.append(ValidationIssue("suite_ids_unique", "Suite IDs are not unique"))

    first = list(pack.iter_cases(selection))
    second = list(pack.iter_cases(selection))
    report.counts["case_count"] = len(first)
    ids = [case.case_id for case in first]
    report.checks["case_ids_unique"] = len(ids) == len(set(ids))
    report.checks["case_ids_stable"] = ids == [case.case_id for case in second]
    report.checks["case_benchmark_matches"] = all(
        case.benchmark_id == info.benchmark_id for case in first
    )
    report.checks["case_suites_exist"] = all(case.suite_id in suite_ids for case in first)
    report.checks["case_records_json_serializable"] = True
    for case in first:
        try:
            json.dumps(case.to_dict(), ensure_ascii=False)
        except (TypeError, ValueError) as error:
            report.checks["case_records_json_serializable"] = False
            report.issues.append(
                ValidationIssue(
                    "case_records_json_serializable",
                    f"Case record is not JSON serializable: {error}",
                    case_id=case.case_id,
                )
            )
    for name, passed in report.checks.items():
        if not passed and not any(issue.gate == name for issue in report.issues):
            report.issues.append(ValidationIssue(name, f"Gate {name!r} failed"))
    if claimed_level != "data":
        report.issues.append(
            ValidationIssue(
                "level_evidence",
                "Generic validation proves only the data level; run benchmark-specific behavioral gates.",
                details={"requested": claimed_level, "verified": "data"},
            )
        )
    return report
