"""AgentDojo native benchmark pack."""

from __future__ import annotations

from collections.abc import Iterable

from agentsim import Env, RunResult, TaskDefine
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

from . import banking, slack, travel, workspace
from .attacks import list_attacks
from .run import BENCHMARK_ID, BENCHMARK_VERSION, DojoEnv, evaluate
from .tasks import iter_tasks

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
            provenance=Provenance(
                source_url="https://github.com/ethz-spylab/agentdojo",
                source_revision="089ed765cc19e73ef17a3f98d4dd455453769a78",
                source_version="0.1.35 / suite v1.2.2",
                extraction_version="agentsim-native-v1",
                license_id="MIT",
            ),
            metadata={
                "suites": list(SUITE_FACTORIES),
                "attack_ids": [attack.name for attack in list_attacks()],
            },
        )

    def suites(self) -> list[SuiteInfo]:
        return [
            SuiteInfo(
                suite_id=name,
                name=f"AgentDojo {name.title()}",
                metadata={
                    "task_count": len(factory().suite.user_tasks),
                    "injection_task_count": len(factory().suite.injection_tasks),
                },
            )
            for name, factory in SUITE_FACTORIES.items()
        ]

    def iter_cases(
        self,
        selection: CaseSelection | None = None,
    ) -> Iterable[BenchmarkCase]:
        selection = selection or CaseSelection()
        if selection.tags:
            raise ValueError("AgentDojo does not currently define case tags")

        kinds = (
            selection.variants
            if selection.variants is not None
            else (
                frozenset({VariantKind.ATTACKED})
                if selection.attack_ids is not None
                else frozenset({VariantKind.CLEAN})
            )
        )
        include_clean = VariantKind.CLEAN in kinds
        include_attacked = VariantKind.ATTACKED in kinds

        if include_clean:
            for suite_id, task in iter_tasks(
                suites=selection.suites,
                user_task_ids=selection.task_ids,
                include_clean=True,
                injection_task_ids=selection.injection_task_ids,
            ):
                yield self.case_for_task(suite_id, task)

        if not include_attacked:
            return
        available = {attack.name for attack in list_attacks() if attack.name != "manual"}
        attack_ids = sorted(selection.attack_ids or available)
        unknown = set(attack_ids) - available
        if unknown:
            raise ValueError("Unknown or non-reproducible AgentDojo attacks: " f"{sorted(unknown)}")
        for attack_id in attack_ids:
            for suite_id, task in iter_tasks(
                suites=selection.suites,
                user_task_ids=selection.task_ids,
                attack=attack_id,
                model_name="AI assistant",
                include_clean=False,
                injection_task_ids=selection.injection_task_ids,
            ):
                yield self.case_for_task(suite_id, task)

    @staticmethod
    def case_for_task(suite_id: str, task: TaskDefine) -> BenchmarkCase:
        attack_id = getattr(task, "attack_method", None)
        injection = getattr(task, "injection", None)
        injection_id = injection.id if injection is not None else None
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
        )

    def create_env(self, suite_or_case: str | BenchmarkCase) -> DojoEnv:
        suite_name = (
            suite_or_case.suite_id if isinstance(suite_or_case, BenchmarkCase) else suite_or_case
        )
        try:
            return SUITE_FACTORIES[suite_name]()
        except KeyError as error:
            raise ValueError(f"Unknown AgentDojo suite: {suite_name!r}") from error

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


benchmark = AgentDojoBenchmark()
