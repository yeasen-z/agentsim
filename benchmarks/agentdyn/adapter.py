"""Benchmark adapter for the native AgentDyn suites."""

from __future__ import annotations

from collections.abc import Iterable

from agentsim import Env, RunResult, TaskDefine
from benchmarks.common.attacks import list_attacks
from benchmarks.common.interfaces import (
    BenchmarkCase,
    BenchmarkInfo,
    CaseSelection,
    CaseVariant,
    EvaluationResult,
    Provenance,
    SuiteInfo,
    VariantKind,
)

from . import dailylife, github, shopping
from .env import BENCHMARK_ID, BENCHMARK_VERSION, AgentDynEnv, evaluate
from .tasks import iter_tasks

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
            provenance=Provenance(
                source_url="https://github.com/SaFo-Lab/AgentDyn",
                source_revision="5353cf7615b135cace8d07c8f12dac53a16b6db3",
                extraction_version="agentsim-native-v1",
                license_id="MIT",
            ),
            metadata={
                "suites": list(SUITE_FACTORIES),
                "user_tasks": 60,
                "attack_cases": 560,
            },
        )

    def suites(self) -> list[SuiteInfo]:
        result = []
        for name, factory in SUITE_FACTORIES.items():
            suite = factory().suite
            result.append(
                SuiteInfo(
                    suite_id=name,
                    name=f"AgentDyn {name.title()}",
                    metadata={
                        "task_count": len(suite.user_tasks),
                        "valid_task_count": sum(
                            task.ground_truth_valid for task in suite.user_tasks.values()
                        ),
                        "injection_task_count": len(suite.injection_tasks),
                    },
                )
            )
        return result

    def iter_cases(
        self,
        selection: CaseSelection | None = None,
    ) -> Iterable[BenchmarkCase]:
        selection = selection or CaseSelection()
        kinds = (
            selection.variants
            if selection.variants is not None
            else (
                frozenset({VariantKind.ATTACKED})
                if selection.attack_ids is not None
                else frozenset({VariantKind.CLEAN})
            )
        )
        if VariantKind.CLEAN in kinds:
            for suite_id, task in iter_tasks(
                suites=selection.suites,
                user_task_ids=selection.task_ids,
                include_clean=True,
                injection_task_ids=selection.injection_task_ids,
            ):
                case = self.case_for_task(suite_id, task)
                if self._matches_tags(case, selection):
                    yield case

        if VariantKind.ATTACKED not in kinds:
            return
        available = {attack.name for attack in list_attacks() if attack.name != "manual"}
        attack_ids = sorted(selection.attack_ids or {"direct"})
        unknown = set(attack_ids) - available
        if unknown:
            raise ValueError("Unknown or non-reproducible AgentDyn attacks: " f"{sorted(unknown)}")
        for attack_id in attack_ids:
            for suite_id, task in iter_tasks(
                suites=selection.suites,
                user_task_ids=selection.task_ids,
                attack=attack_id,
                model_name="AI assistant",
                include_clean=False,
                injection_task_ids=selection.injection_task_ids,
            ):
                case = self.case_for_task(suite_id, task)
                if self._matches_tags(case, selection):
                    yield case

    @staticmethod
    def _matches_tags(case: BenchmarkCase, selection: CaseSelection) -> bool:
        if selection.tags is None:
            return True
        return selection.tags.issubset(case.metadata.get("tags", ()))

    @staticmethod
    def case_for_task(suite_id: str, task: TaskDefine) -> BenchmarkCase:
        attack_id = getattr(task, "attack_method", None)
        injection = getattr(task, "injection", None)
        injection_id = injection.id if injection is not None else None
        valid = bool(task.source and task.source.ground_truth_valid)
        if attack_id is None:
            variant = CaseVariant("clean", VariantKind.CLEAN)
        else:
            variant = CaseVariant(
                f"{attack_id}/{injection_id}",
                VariantKind.ATTACKED,
                attack_id=attack_id,
                injection_task_id=injection_id,
            )
        return BenchmarkCase(
            case_id=f"{BENCHMARK_ID}/{suite_id}/{task.task_id}/{variant.variant_id}",
            benchmark_id=BENCHMARK_ID,
            suite_id=suite_id,
            task=task,
            variant=variant,
            payload=task,
            metadata={
                "ground_truth_valid": valid,
                "tags": ["valid" if valid else "invalid"],
            },
        )

    def create_env(self, suite_or_case: str | BenchmarkCase) -> AgentDynEnv:
        suite_name = (
            suite_or_case.suite_id if isinstance(suite_or_case, BenchmarkCase) else suite_or_case
        )
        try:
            return SUITE_FACTORIES[suite_name]()
        except KeyError as error:
            raise ValueError(f"Unknown AgentDyn suite: {suite_name!r}") from error

    def evaluate(
        self,
        env: Env,
        task_or_case: TaskDefine | BenchmarkCase,
        run: RunResult,
    ) -> EvaluationResult:
        task = task_or_case.task if isinstance(task_or_case, BenchmarkCase) else task_or_case
        result = evaluate(env, task, model_output=str(run.output or ""))
        if isinstance(task_or_case, BenchmarkCase):
            result.case_id = task_or_case.case_id
        return result


benchmark = AgentDynBenchmark()
