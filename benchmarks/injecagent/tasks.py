"""Map pre-composed InjecAgent data into the shared case model."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from benchmarks.common import BenchmarkCase, CaseSelection, CaseVariant, VariantKind

from .env import BENCHMARK_ID, InjecAgentEnv, InjecAgentTask, list_tasks


def iter_cases(
    env: InjecAgentEnv,
    selection: CaseSelection | None = None,
) -> Iterator[BenchmarkCase]:
    """Yield stable attacked cases without inventing an upstream clean variant."""
    selection = selection or CaseSelection()
    if selection.suites is not None and BENCHMARK_ID not in selection.suites:
        return
    kinds = selection.variants or frozenset(VariantKind)
    if VariantKind.ATTACKED not in kinds:
        return

    for task in list_tasks(env):
        source = task.source
        if source is None:
            continue
        if selection.task_ids is not None and task.task_id not in selection.task_ids:
            continue
        if selection.attack_ids is not None and task.attack_mode not in selection.attack_ids:
            continue
        if selection.injection_task_ids is not None:
            continue
        tags = frozenset({task.attack_mode, source.attack_type})
        if selection.tags is not None and not selection.tags.issubset(tags):
            continue

        yield case_for_task(task)


def case_for_task(task: InjecAgentTask) -> BenchmarkCase:
    """Wrap one legacy task with its stable native case identity."""
    source = task.source
    if source is None:
        raise ValueError("InjecAgent task has no source case")
    variant = CaseVariant(
        variant_id=f"{task.attack_mode}/{source.case_id}",
        kind=VariantKind.ATTACKED,
        attack_id=task.attack_mode,
        metadata={
            "attack_mode": task.attack_mode,
            "attack_type": source.attack_type,
            "attacker_tools": list(source.attacker_tools),
            "precomposed": True,
        },
    )
    return BenchmarkCase(
        case_id=f"{BENCHMARK_ID}/{BENCHMARK_ID}/{source.case_id}",
        benchmark_id=BENCHMARK_ID,
        suite_id=BENCHMARK_ID,
        task=task,
        variant=variant,
        payload=source,
        metadata={"source_case_id": source.case_id},
    )


def case_ids(cases: Iterable[BenchmarkCase]) -> list[str]:
    """Return case IDs for compatibility checks and research scripts."""
    return [case.case_id for case in cases]
