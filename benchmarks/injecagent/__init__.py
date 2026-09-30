"""InjecAgent benchmark adapted to AgentSim's runtime."""

from benchmarks.common.interfaces import EvaluationResult
from benchmarks.common.registry import benchmark_registry

from .adapter import InjecAgentBenchmark, benchmark
from .data import InjecAgentData, TestCase, ToolSpec
from .env import InjecAgentEnv, InjecAgentState, InjecAgentTask, list_envs, list_tasks
from .evaluation import compute_aggregate_scores, evaluate
from .runner import run_suite, run_task, traverse
from .tasks import iter_cases

if benchmark.info().benchmark_id not in benchmark_registry.list():
    benchmark_registry.register(benchmark)

__all__ = [
    "InjecAgentBenchmark",
    "InjecAgentData",
    "InjecAgentEnv",
    "InjecAgentState",
    "InjecAgentTask",
    "TestCase",
    "ToolSpec",
    "EvaluationResult",
    "benchmark",
    "compute_aggregate_scores",
    "evaluate",
    "list_envs",
    "list_tasks",
    "iter_cases",
    "run_suite",
    "run_task",
    "traverse",
]
