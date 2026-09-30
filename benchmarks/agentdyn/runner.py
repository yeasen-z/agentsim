"""Task loading and execution helpers for AgentDyn."""

from pathlib import Path
from typing import Iterable, Optional

from agentsim import EpisodeRuntime
from benchmarks.common.runner import run_case
from benchmarks.common.runner import traverse as traverse_benchmark

from .adapter import benchmark


def run_task(suite: str, task, scaffold, *, max_scaffold_turns: int = 100):
    return run_case(
        benchmark,
        benchmark.case_for_task(suite, task),
        scaffold,
        runtime=EpisodeRuntime(max_scaffold_turns=max_scaffold_turns),
    )


def traverse(
    tasks: Iterable[tuple[str, object]],
    scaffold_factory,
    *,
    output_path: Optional[str | Path] = None,
    max_tasks: Optional[int] = None,
    max_scaffold_turns: int = 100,
):
    cases = (benchmark.case_for_task(suite, task) for suite, task in tasks)
    return traverse_benchmark(
        benchmark,
        cases,
        scaffold_factory,
        output_path=output_path,
        max_tasks=max_tasks,
        runtime_factory=lambda: EpisodeRuntime(max_scaffold_turns=max_scaffold_turns),
    )
