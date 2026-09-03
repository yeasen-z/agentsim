"""Task loading and execution helpers for AgentDyn."""

from pathlib import Path
from typing import Iterable, Optional

from agentsim import EpisodeRuntime
from benchmarks.common.runner import run_task as run_benchmark_task, traverse as traverse_benchmark

from .adapter import benchmark
from .tasks import iter_tasks


def run_task(suite: str, task, scaffold, *, max_scaffold_turns: int = 100):
    return run_benchmark_task(benchmark, benchmark.create_env(suite), task, scaffold, runtime=EpisodeRuntime(max_scaffold_turns=max_scaffold_turns))


def traverse(tasks: Iterable[tuple[str, object]], scaffold_factory, *, output_path: Optional[str | Path] = None, max_tasks: Optional[int] = None, max_scaffold_turns: int = 100):
    return traverse_benchmark(benchmark, ((benchmark.create_env(suite), task) for suite, task in tasks), scaffold_factory, output_path=output_path, max_tasks=max_tasks, runtime_factory=lambda: EpisodeRuntime(max_scaffold_turns=max_scaffold_turns))
