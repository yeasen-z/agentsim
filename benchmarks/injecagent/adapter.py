"""InjecAgent benchmark adapter."""

from __future__ import annotations

from agentsim import Env, RunResult, TaskDefine
from benchmarks.common.interfaces import (
    BenchmarkCase,
    BenchmarkInfo,
    CaseSelection,
    EvaluationResult,
    Provenance,
    SuiteInfo,
)

from .data import InjecAgentData
from .env import BENCHMARK_ID, BENCHMARK_VERSION, InjecAgentEnv, list_envs, list_tasks
from .evaluation import evaluate
from .tasks import iter_cases


class InjecAgentBenchmark:
    """Benchmark adapter for InjecAgent indirect prompt injection benchmark."""

    def __init__(self, data: InjecAgentData | None = None):
        self._data = data

    @property
    def data(self) -> InjecAgentData:
        if self._data is None:
            self._data = InjecAgentData.load()
        return self._data

    def info(self) -> BenchmarkInfo:
        return BenchmarkInfo(
            benchmark_id=BENCHMARK_ID,
            version=BENCHMARK_VERSION,
            description="InjecAgent indirect prompt injection benchmark for tool-integrated LLM agents",
            primary_metric="asr",
            provenance=Provenance(
                source_url="https://github.com/uiuc-kang-lab/InjecAgent",
                source_revision="f19c9f2c79a41046eb13c03c51a24c567a8ffa07",
                extraction_version="agentsim-native-v1",
                data_digest="sha256:6a88a7aa88018e404c60b8b8f36bee07c28cc84a3975c2ada214c2445ed91a18",
                license_id="MIT",
            ),
            metadata={
                "attack_modes": ["dh", "ds"],
                "total_cases": len(self.data.all_cases),
            },
        )

    def suites(self) -> list[SuiteInfo]:
        return [
            SuiteInfo(
                suite_id=BENCHMARK_ID,
                name="InjecAgent",
                metadata={
                    "case_count": len(self.data.all_cases),
                    "attack_modes": ["dh", "ds"],
                },
            )
        ]

    def iter_cases(self, selection: CaseSelection | None = None):
        return iter_cases(InjecAgentEnv(self.data), selection)

    def create_env(self, case: BenchmarkCase | None = None) -> InjecAgentEnv:
        if case is not None and case.benchmark_id != BENCHMARK_ID:
            raise ValueError(f"Expected an InjecAgent case, got {case.benchmark_id!r}")
        return InjecAgentEnv(self.data)

    def list_envs(self) -> list[InjecAgentEnv]:
        return list_envs()

    def list_tasks(self, env: Env) -> list[TaskDefine]:
        return list_tasks(env)

    def evaluate(
        self,
        env: Env,
        task_or_case: TaskDefine | BenchmarkCase,
        run: RunResult,
    ) -> EvaluationResult:
        task = task_or_case.task if isinstance(task_or_case, BenchmarkCase) else task_or_case
        result = evaluate(env, task, run)
        if isinstance(task_or_case, BenchmarkCase):
            result.case_id = task_or_case.case_id
        return result


benchmark = InjecAgentBenchmark()
