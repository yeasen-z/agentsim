"""AgentDojo selection helpers backed by the common benchmark runner."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Iterator, Optional

from agentsim import EpisodeRuntime, ScaffoldAPI
from benchmarks.common.runner import BenchmarkRun, run_case
from benchmarks.common.runner import traverse as traverse_benchmark

from .adapter import benchmark
from .attacks import Attack
from .tasks import iter_tasks


def iter_suite_tasks(
    *,
    suites: Optional[Iterable[str]] = None,
    user_task_ids: Optional[Iterable[str]] = None,
    attack: str | Attack | None = None,
    model_name: Optional[str] = None,
    include_clean: bool = True,
    injection_task_ids: Optional[Iterable[str]] = None,
) -> Iterator[tuple[str, object]]:
    return iter_tasks(
        suites=suites,
        user_task_ids=user_task_ids,
        attack=attack,
        model_name=model_name,
        include_clean=include_clean,
        injection_task_ids=injection_task_ids,
    )


def run_task(
    suite_name: str,
    task,
    scaffold: ScaffoldAPI,
    *,
    max_scaffold_turns: int = 100,
) -> BenchmarkRun:
    case = benchmark.case_for_task(suite_name, task)
    return run_case(
        benchmark,
        case,
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
    cases = (benchmark.case_for_task(suite_name, task) for suite_name, task in tasks)
    return traverse_benchmark(
        benchmark,
        cases,
        scaffold_factory,
        output_path=output_path,
        max_tasks=max_tasks,
        runtime_factory=lambda: EpisodeRuntime(max_scaffold_turns=max_scaffold_turns),
    )
