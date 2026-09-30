"""Common contracts shared by all benchmark adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, Mapping, Optional, Protocol, Union, runtime_checkable

from agentsim.interfaces import Env, RunResult
from agentsim.task import TaskDefine

MetricValue = Optional[Union[bool, int, float, str]]


@dataclass(frozen=True)
class Provenance:
    """Identity of the upstream content represented by a native pack."""

    source_url: str
    source_revision: str
    source_version: Optional[str] = None
    extraction_version: Optional[str] = None
    data_digest: Optional[str] = None
    license_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "source_url": self.source_url,
            "source_revision": self.source_revision,
            "source_version": self.source_version,
            "extraction_version": self.extraction_version,
            "data_digest": self.data_digest,
            "license_id": self.license_id,
        }


@dataclass(frozen=True)
class BenchmarkInfo:
    benchmark_id: str
    version: str
    description: str = ""
    primary_metric: Optional[str] = None
    provenance: Optional[Provenance] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "version": self.version,
            "description": self.description,
            "primary_metric": self.primary_metric,
            "provenance": self.provenance.to_dict() if self.provenance is not None else None,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SuiteInfo:
    """Stable public identity for one benchmark suite."""

    suite_id: str
    name: str
    description: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.suite_id:
            raise ValueError("SuiteInfo.suite_id must not be empty")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "name": self.name,
            "description": self.description,
            "metadata": dict(self.metadata),
        }


class VariantKind(str, Enum):
    """The two case shapes understood by the generic campaign runner."""

    CLEAN = "clean"
    ATTACKED = "attacked"


@dataclass(frozen=True)
class CaseVariant:
    """A fully specified clean or attacked variant of one user task."""

    variant_id: str
    kind: VariantKind
    attack_id: Optional[str] = None
    injection_task_id: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.variant_id:
            raise ValueError("CaseVariant.variant_id must not be empty")
        if isinstance(self.kind, str):
            object.__setattr__(self, "kind", VariantKind(self.kind))
        if self.kind is VariantKind.CLEAN and (
            self.attack_id is not None or self.injection_task_id is not None
        ):
            raise ValueError("Clean variants cannot identify an attack or injection task")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "kind": self.kind.value,
            "attack_id": self.attack_id,
            "injection_task_id": self.injection_task_id,
            "metadata": dict(self.metadata),
        }


@dataclass
class BenchmarkCase:
    """One stable benchmark case consumed by the shared runner.

    ``payload`` is owned by the concrete benchmark pack. Generic code records
    its public metadata but must not inspect or serialize the payload.
    """

    case_id: str
    benchmark_id: str
    suite_id: str
    task: TaskDefine
    variant: CaseVariant
    payload: Any = field(default=None, repr=False, compare=False)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("BenchmarkCase.case_id must not be empty")
        if not self.benchmark_id:
            raise ValueError("BenchmarkCase.benchmark_id must not be empty")
        if not self.suite_id:
            raise ValueError("BenchmarkCase.suite_id must not be empty")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "benchmark_id": self.benchmark_id,
            "suite_id": self.suite_id,
            "task": self.task.to_dict(),
            "variant": self.variant.to_dict(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class CaseSelection:
    """Benchmark-independent filters used when enumerating cases."""

    suites: Optional[frozenset[str]] = None
    task_ids: Optional[frozenset[str]] = None
    variants: Optional[frozenset[VariantKind]] = None
    attack_ids: Optional[frozenset[str]] = None
    injection_task_ids: Optional[frozenset[str]] = None
    tags: Optional[frozenset[str]] = None

    def __post_init__(self) -> None:
        for name in (
            "suites",
            "task_ids",
            "attack_ids",
            "injection_task_ids",
            "tags",
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, frozenset):
                object.__setattr__(self, name, frozenset(value))
        if self.variants is not None:
            variants = frozenset(VariantKind(value) for value in self.variants)
            object.__setattr__(self, "variants", variants)

    def to_dict(self) -> Dict[str, Any]:
        def ordered(value: Optional[frozenset[str]]) -> Optional[list[str]]:
            return sorted(value) if value is not None else None

        return {
            "suites": ordered(self.suites),
            "task_ids": ordered(self.task_ids),
            "variants": (
                sorted(value.value for value in self.variants)
                if self.variants is not None
                else None
            ),
            "attack_ids": ordered(self.attack_ids),
            "injection_task_ids": ordered(self.injection_task_ids),
            "tags": ordered(self.tags),
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


@runtime_checkable
class NativeBenchmarkPack(Protocol):
    """Complete contract for native case enumeration and evaluation."""

    def info(self) -> BenchmarkInfo: ...

    def suites(self) -> list[SuiteInfo]: ...

    def iter_cases(
        self,
        selection: Optional[CaseSelection] = None,
    ) -> Iterable[BenchmarkCase]: ...

    def create_env(self, case: BenchmarkCase) -> Any: ...

    def evaluate(
        self,
        env: Any,
        case: BenchmarkCase,
        run: RunResult,
    ) -> EvaluationResult: ...
