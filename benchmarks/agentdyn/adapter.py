"""Benchmark adapter for the native AgentDyn suites."""

from __future__ import annotations

from agentsim import Env, RunResult, TaskDefine
from benchmarks.common.interfaces import BenchmarkInfo, EvaluationResult

from . import dailylife, github, shopping
from .env import BENCHMARK_ID, BENCHMARK_VERSION, AgentDynEnv, evaluate

SUITE_FACTORIES = {
    "shopping": shopping.create_env,
    "github": github.create_env,
    "dailylife": dailylife.create_env,
}


class AgentDynBenchmark:
    def info(self) -> BenchmarkInfo:
        return BenchmarkInfo(
            benchmark_id=BENCHMARK_ID,
            version=BENCHMARK_VERSION,
            description="AgentDyn dynamic indirect prompt-injection benchmark",
            primary_metric="secure_utility",
            metadata={
                "suites": list(SUITE_FACTORIES),
                "user_tasks": 60,
                "attack_cases": 560,
            },
        )

    def create_env(self, suite_name: str) -> AgentDynEnv:
        try:
            return SUITE_FACTORIES[suite_name]()
        except KeyError as error:
            raise ValueError(f"Unknown AgentDyn suite: {suite_name!r}") from error

    def evaluate(self, env: Env, task: TaskDefine, run: RunResult) -> EvaluationResult:
        return evaluate(env, task, model_output=str(run.output or ""))


benchmark = AgentDynBenchmark()
