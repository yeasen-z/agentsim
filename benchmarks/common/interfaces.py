"""Common contracts shared by all benchmark adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional, Protocol, Union, runtime_checkable

from agentsim.interfaces import Env, RunResult
from agentsim.task import TaskDefine

MetricValue = Optional[Union[bool, int, float, str]]


@dataclass(frozen=True)
class BenchmarkInfo:
    benchmark_id: str
    version: str
    description: str = ""
    primary_metric: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "version": self.version,
            "description": self.description,
            "primary_metric": self.primary_metric,
            "metadata": dict(self.metadata),
        }


@dataclass
class EvaluationResult:
    """Normalized metrics plus benchmark-owned details."""

    benchmark_id: str
    benchmark_version: str
    case_id: str
    metrics: Dict[str, MetricValue]
    primary_metric: Optional[str] = None
    passed: Optional[bool] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "benchmark_version": self.benchmark_version,
            "case_id": self.case_id,
            "primary_metric": self.primary_metric,
            "passed": self.passed,
            "metrics": self.metrics,
            "metadata": self.metadata,
        }


@runtime_checkable
class BenchmarkAdapter(Protocol):
    """A benchmark owns suite environments and evaluation semantics."""

    def info(self) -> BenchmarkInfo: ...

    def evaluate(
        self,
        env: Env,
        task: TaskDefine,
        run: RunResult,
    ) -> EvaluationResult: ...
