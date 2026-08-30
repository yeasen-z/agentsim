"""Registry for benchmark adapters, separate from environment scenarios."""

from __future__ import annotations

from typing import Dict, List

from .interfaces import BenchmarkAdapter


class BenchmarkRegistry:
    def __init__(self) -> None:
        self._adapters: Dict[str, BenchmarkAdapter] = {}

    def register(self, adapter: BenchmarkAdapter) -> None:
        if not isinstance(adapter, BenchmarkAdapter):
            raise TypeError("adapter must implement BenchmarkAdapter")
        benchmark_id = adapter.info().benchmark_id
        if benchmark_id in self._adapters:
            raise ValueError(f"Benchmark already registered: {benchmark_id}")
        self._adapters[benchmark_id] = adapter

    def get(self, benchmark_id: str) -> BenchmarkAdapter:
        try:
            return self._adapters[benchmark_id]
        except KeyError as error:
            raise KeyError(f"Unknown benchmark: {benchmark_id}") from error

    def list(self) -> List[str]:
        return sorted(self._adapters)

    def clear(self) -> None:
        self._adapters.clear()


benchmark_registry = BenchmarkRegistry()
