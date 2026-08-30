"""AgentDojo adapter: suites provide environments, tasks remain plain records."""

from __future__ import annotations

from benchmarks.common.interfaces import BenchmarkInfo, EvaluationResult
from agentsim import Env, RunResult, TaskDefine

from . import banking, slack, travel, workspace
from .run import BENCHMARK_ID, BENCHMARK_VERSION, DojoEnv, evaluate

SUITE_FACTORIES = {
    "workspace": workspace.create_env,
    "travel": travel.create_env,
    "banking": banking.create_env,
    "slack": slack.create_env,
}


class AgentDojoBenchmark:
    def info(self) -> BenchmarkInfo:
        return BenchmarkInfo(
            benchmark_id=BENCHMARK_ID,
            version=BENCHMARK_VERSION,
            description="AgentDojo indirect prompt-injection benchmark",
            primary_metric="secure_utility",
            metadata={"suites": list(SUITE_FACTORIES)},
        )

    def create_env(self, suite_name: str) -> DojoEnv:
        try:
            return SUITE_FACTORIES[suite_name]()
        except KeyError as error:
            raise ValueError(f"Unknown AgentDojo suite: {suite_name!r}") from error

    def evaluate(self, env: Env, task: TaskDefine, run: RunResult) -> EvaluationResult:
        return evaluate(env, task, model_output=str(run.output or ""))


benchmark = AgentDojoBenchmark()
