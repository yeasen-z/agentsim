"""AgentDyn benchmark adapted to AgentSim's four-layer architecture."""

from benchmarks.common.registry import benchmark_registry
from benchmarks.agentdojo.attacks import Attack, list_attacks

from .adapter import AgentDynBenchmark, benchmark
from . import dailylife, github, shopping
from .env import AgentDynEnv, AgentDynState, build_tasks, evaluate, list_envs, list_tasks
from .runner import run_task, traverse
from .tasks import TASKS, iter_tasks

if benchmark.info().benchmark_id not in benchmark_registry.list():
    benchmark_registry.register(benchmark)

__all__ = [
    "AgentDynBenchmark",
    "AgentDynEnv",
    "AgentDynState",
    "Attack",
    "TASKS",
    "benchmark",
    "build_tasks",
    "dailylife",
    "evaluate",
    "github",
    "iter_tasks",
    "list_attacks",
    "list_envs",
    "list_tasks",
    "run_task",
    "shopping",
    "traverse",
]
