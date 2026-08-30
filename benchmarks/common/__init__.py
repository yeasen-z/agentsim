"""Benchmark contracts, registry, shared runner, and built-in adapters."""

from .interfaces import (
    BenchmarkAdapter,
    BenchmarkInfo,
    EvaluationResult,
    MetricValue,
)
from .registry import BenchmarkRegistry, benchmark_registry
from .runner import BenchmarkRun, run_task, traverse

__all__ = [
    "BenchmarkAdapter",
    "BenchmarkInfo",
    "BenchmarkRegistry",
    "BenchmarkRun",
    "EvaluationResult",
    "MetricValue",
    "benchmark_registry",
    "run_task",
    "traverse",
]
