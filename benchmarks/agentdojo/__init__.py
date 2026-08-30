"""AgentDojo benchmark data adapted to AgentSim's runtime."""

from benchmarks.common.interfaces import EvaluationResult
from benchmarks.common.registry import benchmark_registry

from .adapter import AgentDojoBenchmark, benchmark
from .attacks import Attack, list_attacks
from .run import build_tasks, evaluate, list_envs, list_tasks
from .runner import iter_suite_tasks, run_task, traverse
from . import banking, slack, travel, workspace, tasks

if benchmark.info().benchmark_id not in benchmark_registry.list():
    benchmark_registry.register(benchmark)

__all__ = [
    "AgentDojoBenchmark",
    "Attack",
    "EvaluationResult",
    "benchmark",
    "build_tasks",
    "evaluate",
    "list_attacks",
    "list_envs",
    "list_tasks",
    "iter_suite_tasks",
    "run_task",
    "traverse",
    "tasks",
    "workspace",
    "travel",
    "banking",
    "slack",
]
