"""InjecAgent benchmark runner utilities."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from agentsim import EpisodeRuntime, RunResult
from benchmarks.common.interfaces import EvaluationResult
from benchmarks.common.runner import run_case

from .adapter import benchmark
from .env import InjecAgentEnv, InjecAgentTask, list_envs, list_tasks
from .evaluation import compute_aggregate_scores
from .tasks import case_for_task


def run_task(
    env: InjecAgentEnv,
    task: InjecAgentTask,
    scaffold_factory,
    max_scaffold_turns: int = 10,
) -> tuple[RunResult, EvaluationResult]:
    """Run a single InjecAgent task and return the result with evaluation."""
    scaffold = scaffold_factory()
    runtime = EpisodeRuntime(max_scaffold_turns=max_scaffold_turns)
    result = run_case(
        benchmark,
        case_for_task(task),
        scaffold,
        runtime=runtime,
        env_override=env,
    )
    return result.execution, result.evaluation


def traverse(
    tasks: Iterable[InjecAgentTask],
    scaffold_factory,
    *,
    max_tasks: Optional[int] = None,
    max_scaffold_turns: int = 10,
) -> List[Dict[str, Any]]:
    """Run multiple InjecAgent tasks and collect results."""
    env = list_envs()[0]

    results = []
    for i, task in enumerate(tasks):
        if max_tasks is not None and i >= max_tasks:
            break

        env_fresh = env.fresh()
        run_result, eval_result = run_task(env_fresh, task, scaffold_factory, max_scaffold_turns)

        results.append(
            {
                "case_id": task.task_id,
                "attack_mode": task.attack_mode,
                "attack_type": task.source.attack_type if task.source else None,
                "run_status": run_result.status,
                "evaluation": eval_result.to_dict(),
            }
        )

    return results


def run_suite(
    scaffold_factory,
    attack_mode: Optional[str] = None,
    max_tasks: Optional[int] = None,
    max_scaffold_turns: int = 10,
) -> Dict[str, Any]:
    """Run the full InjecAgent suite or a subset.

    Args:
        scaffold_factory: Callable that creates a scaffold for each task
        attack_mode: Filter by "dh" or "ds", or None for all
        max_tasks: Maximum number of tasks to run
        max_scaffold_turns: Maximum scaffold turns per task

    Returns:
        Dictionary with results and aggregate scores
    """
    envs = list_envs()
    if not envs:
        raise RuntimeError("No InjecAgent environments available")
    env = envs[0]

    all_tasks = list_tasks(env)
    if attack_mode:
        all_tasks = [t for t in all_tasks if t.attack_mode == attack_mode]

    results = traverse(
        all_tasks,
        scaffold_factory,
        max_tasks=max_tasks,
        max_scaffold_turns=max_scaffold_turns,
    )

    eval_results = []
    for r in results:
        eval_results.append(
            EvaluationResult(
                benchmark_id=r["evaluation"]["benchmark_id"],
                benchmark_version=r["evaluation"]["benchmark_version"],
                case_id=r["evaluation"]["case_id"],
                metrics=r["evaluation"]["metrics"],
                primary_metric=r["evaluation"]["primary_metric"],
                passed=r["evaluation"]["passed"],
                metadata=r["evaluation"]["metadata"],
            )
        )

    scores = compute_aggregate_scores(eval_results)

    return {
        "results": results,
        "scores": scores,
        "total_tasks": len(all_tasks),
        "executed_tasks": len(results),
    }
