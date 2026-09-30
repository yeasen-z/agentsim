"""Benchmark contracts, registry, shared runner, and built-in adapters."""

from .attacks import Attack, list_attacks, resolve_attack
from .interfaces import (
    BenchmarkAdapter,
    BenchmarkCase,
    BenchmarkInfo,
    CaseSelection,
    CaseVariant,
    EvaluationResult,
    MetricValue,
    NativeBenchmarkPack,
    Provenance,
    SuiteInfo,
    VariantKind,
)
from .registry import BenchmarkRegistry, benchmark_registry
from .runner import (
    BenchmarkRun,
    CampaignSpec,
    CampaignSummary,
    JsonlResultStore,
    ResultStore,
    run_campaign,
    run_case,
    run_task,
    stable_run_id,
    traverse,
)
from .validation import ValidationIssue, ValidationReport, validate_pack

__all__ = [
    "Attack",
    "BenchmarkAdapter",
    "BenchmarkCase",
    "BenchmarkInfo",
    "BenchmarkRegistry",
    "BenchmarkRun",
    "CampaignSpec",
    "CampaignSummary",
    "CaseSelection",
    "CaseVariant",
    "EvaluationResult",
    "MetricValue",
    "NativeBenchmarkPack",
    "Provenance",
    "JsonlResultStore",
    "ResultStore",
    "SuiteInfo",
    "VariantKind",
    "ValidationIssue",
    "ValidationReport",
    "benchmark_registry",
    "list_attacks",
    "resolve_attack",
    "run_campaign",
    "run_case",
    "run_task",
    "stable_run_id",
    "traverse",
    "validate_pack",
]
