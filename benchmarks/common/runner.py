"""Benchmark-independent task execution and JSONL persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from agentsim.interfaces import Env, RunResult, ScaffoldAPI, as_env
from agentsim.task import TaskDefine
from agentsim.runtime import EpisodeRuntime
from .interfaces import BenchmarkAdapter, EvaluationResult


@dataclass
class BenchmarkRun:
    """Execution and evaluation for one environment/task pair."""

    env: Env
    task: TaskDefine
    execution: RunResult
    evaluation: EvaluationResult

    def to_dict(self, *, include_trace: bool = True) -> Dict[str, Any]:
        execution = self.execution.to_dict()
        if not include_trace:
            execution["trace"] = None
        return {
            "task_id": self.task.task_id,
            "scenario_id": self.task.scenario,
            "execution": execution,
            "evaluation": self.evaluation.to_dict(),
        }


def run_task(
    adapter: BenchmarkAdapter,
    env: Env,
    task: TaskDefine,
    scaffold: ScaffoldAPI,
    *,
    runtime: Optional[EpisodeRuntime] = None,
    runtime_config: Optional[Dict[str, Any]] = None,
) -> BenchmarkRun:
    """Execute and evaluate one task on one benchmark-owned environment."""
    runtime = runtime or EpisodeRuntime()
    execution = runtime.run(
        as_env(env),
        scaffold,
        task,
        instruction=task.description,
        config=runtime_config,
    )
    evaluation = adapter.evaluate(env, task, execution)
    execution.trace.metadata["benchmark"] = {
        "info": adapter.info().to_dict(),
        "task_id": task.task_id,
        "scenario_id": task.scenario,
        "evaluation": evaluation.to_dict(),
    }
    return BenchmarkRun(env=env, task=task, execution=execution, evaluation=evaluation)


def traverse(
    adapter: BenchmarkAdapter,
    tasks: Iterable[tuple[Env, TaskDefine]],
    scaffold_factory: Callable[[], ScaffoldAPI],
    *,
    output_path: Optional[str | Path] = None,
    max_tasks: Optional[int] = None,
    runtime_factory: Callable[[], EpisodeRuntime] = EpisodeRuntime,
    runtime_config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Run environment/task pairs and optionally append JSONL records."""
    selected = tasks if max_tasks is None else islice(tasks, max_tasks)
    output = Path(output_path) if output_path is not None else None
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.touch(exist_ok=False)

    summaries: List[Dict[str, Any]] = []
    for env, task in selected:
        try:
            benchmark_run = run_task(
                adapter,
                env,
                task,
                scaffold_factory(),
                runtime=runtime_factory(),
                runtime_config=runtime_config,
            )
            evaluation = benchmark_run.evaluation
            summary = {
                "task_id": task.task_id,
                "scenario_id": task.scenario,
                "status": benchmark_run.execution.status,
                "env_steps": benchmark_run.execution.env_steps,
                "scaffold_turns": benchmark_run.execution.scaffold_turns,
                "output": benchmark_run.execution.output,
                "passed": evaluation.passed,
                "metrics": evaluation.metrics,
                "error": benchmark_run.execution.metadata.get("error"),
            }
            details = benchmark_run.to_dict(include_trace=True)
        except Exception as error:
            summary = {
                "task_id": task.task_id,
                "scenario_id": task.scenario,
                "status": "error",
                "env_steps": 0,
                "scaffold_turns": 0,
                "output": None,
                "passed": False,
                "metrics": {},
                "error": f"{type(error).__name__}: {error}",
            }
            details = {"task_id": task.task_id, "scenario_id": task.scenario, "error": summary["error"]}

        summaries.append(summary)
        if output is not None:
            with output.open("a", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(
                        {"summary": summary, "details": details},
                        ensure_ascii=False,
                        default=str,
                    )
                    + "\n"
                )
    return summaries
