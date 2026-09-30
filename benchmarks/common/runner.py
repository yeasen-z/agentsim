"""Benchmark-independent task execution and JSONL persistence."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from itertools import islice
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol

from agentsim.interfaces import Env, RunResult, ScaffoldAPI, as_env
from agentsim.runtime import EpisodeRuntime
from agentsim.task import TaskDefine

from .interfaces import (
    BenchmarkAdapter,
    BenchmarkCase,
    CaseSelection,
    EvaluationResult,
    NativeBenchmarkPack,
)


@dataclass(frozen=True)
class CampaignSpec:
    """A reproducible serial campaign over selected benchmark cases."""

    campaign_id: str
    selection: CaseSelection = CaseSelection()
    seeds: tuple[int, ...] = (42,)
    repetitions: int = 1
    max_cases: Optional[int] = None
    max_scaffold_turns: int = 100

    def __post_init__(self) -> None:
        if not self.campaign_id:
            raise ValueError("CampaignSpec.campaign_id must not be empty")
        object.__setattr__(self, "seeds", tuple(self.seeds))
        if not self.seeds:
            raise ValueError("CampaignSpec.seeds must not be empty")
        if len(self.seeds) != len(set(self.seeds)):
            raise ValueError("CampaignSpec.seeds must not contain duplicates")
        if self.repetitions < 1:
            raise ValueError("CampaignSpec.repetitions must be positive")
        if self.max_cases is not None and self.max_cases < 0:
            raise ValueError("CampaignSpec.max_cases must not be negative")
        if self.max_scaffold_turns < 1:
            raise ValueError("CampaignSpec.max_scaffold_turns must be positive")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "selection": self.selection.to_dict(),
            "seeds": list(self.seeds),
            "repetitions": self.repetitions,
            "max_cases": self.max_cases,
            "max_scaffold_turns": self.max_scaffold_turns,
        }


@dataclass
class CampaignSummary:
    campaign_id: str
    selected_cases: int = 0
    planned_runs: int = 0
    executed_runs: int = 0
    skipped_runs: int = 0
    error_runs: int = 0
    by_suite: Dict[str, int] = field(default_factory=dict)
    by_variant: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "selected_cases": self.selected_cases,
            "planned_runs": self.planned_runs,
            "executed_runs": self.executed_runs,
            "skipped_runs": self.skipped_runs,
            "error_runs": self.error_runs,
            "by_suite": dict(self.by_suite),
            "by_variant": dict(self.by_variant),
        }


class ResultStore(Protocol):
    def completed_run_ids(self) -> set[str]: ...

    def write_manifest(self, manifest: Dict[str, Any]) -> None: ...

    def append(self, record: Dict[str, Any]) -> None: ...


class JsonlResultStore:
    """Append-only JSONL records plus one resumable campaign manifest."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.manifest_path = self.root / "manifest.json"
        self.records_path = self.root / "records.jsonl"

    def completed_run_ids(self) -> set[str]:
        if not self.records_path.exists():
            return set()
        completed: set[str] = set()
        with self.records_path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    record = json.loads(line)
                    if record.get("status") == "completed":
                        completed.add(record["run_id"])
        return completed

    def write_manifest(self, manifest: Dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )

    def append(self, record: Dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.records_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            stream.flush()


def stable_run_id(
    pack: NativeBenchmarkPack,
    case: BenchmarkCase,
    *,
    seed: int,
    repetition: int,
    campaign_id: Optional[str] = None,
) -> str:
    identity = {
        "benchmark_id": pack.info().benchmark_id,
        "benchmark_version": pack.info().version,
        "case_id": case.case_id,
        "seed": seed,
        "repetition": repetition,
        "campaign_id": campaign_id,
    }
    digest = sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return digest[:24]


@dataclass
class BenchmarkRun:
    """Execution and evaluation for one environment/task pair."""

    env: Any
    task: TaskDefine
    execution: RunResult
    evaluation: EvaluationResult
    case: Optional[BenchmarkCase] = None

    def to_dict(self, *, include_trace: bool = True) -> Dict[str, Any]:
        execution = self.execution.to_dict()
        if not include_trace:
            execution["trace"] = None
        result = {
            "task_id": self.task.task_id,
            "scenario_id": self.task.scenario,
            "execution": execution,
            "evaluation": self.evaluation.to_dict(),
        }
        if self.case is not None:
            result.update(
                {
                    "case_id": self.case.case_id,
                    "benchmark_id": self.case.benchmark_id,
                    "suite_id": self.case.suite_id,
                    "variant": self.case.variant.to_dict(),
                }
            )
        return result


def _runtime_env(env: Any) -> Env:
    """Return an environment runtime view without wrapping it twice."""
    return env if isinstance(env, Env) else as_env(env)


def run_task(
    adapter: BenchmarkAdapter,
    env: Env,
    task: TaskDefine,
    scaffold: ScaffoldAPI,
    *,
    runtime: Optional[EpisodeRuntime] = None,
    runtime_config: Optional[Dict[str, Any]] = None,
) -> BenchmarkRun:
    """Execute and evaluate one task on one benchmark-owned environment."""
    runtime = runtime or EpisodeRuntime()
    execution = runtime.run(
        _runtime_env(env),
        scaffold,
        task,
        instruction=task.description,
        config=runtime_config,
    )
    evaluation = adapter.evaluate(env, task, execution)
    execution.trace.metadata["benchmark"] = {
        "info": adapter.info().to_dict(),
        "task_id": task.task_id,
        "scenario_id": task.scenario,
        "evaluation": evaluation.to_dict(),
    }
    return BenchmarkRun(env=env, task=task, execution=execution, evaluation=evaluation)


def run_case(
    pack: NativeBenchmarkPack,
    case: BenchmarkCase,
    scaffold: ScaffoldAPI,
    *,
    runtime: Optional[EpisodeRuntime] = None,
    runtime_config: Optional[Dict[str, Any]] = None,
    env_override: Any = None,
) -> BenchmarkRun:
    """Execute a fully specified native benchmark case.

    The shared runner owns execution and trace normalization. Environment
    construction and evaluation remain benchmark-owned extension points.
    """
    info = pack.info()
    if case.benchmark_id != info.benchmark_id:
        raise ValueError(
            f"Case benchmark {case.benchmark_id!r} does not match pack " f"{info.benchmark_id!r}"
        )
    runtime = runtime or EpisodeRuntime()
    env = pack.create_env(case) if env_override is None else env_override
    execution = runtime.run(
        _runtime_env(env),
        scaffold,
        case.task,
        instruction=case.task.description,
        config=runtime_config,
    )
    evaluation = pack.evaluate(env, case, execution)
    execution.trace.metadata["benchmark"] = {
        "info": info.to_dict(),
        "case": case.to_dict(),
        "evaluation": evaluation.to_dict(),
    }
    return BenchmarkRun(
        env=env,
        task=case.task,
        execution=execution,
        evaluation=evaluation,
        case=case,
    )


def run_campaign(
    pack: NativeBenchmarkPack,
    scaffold_factory: Callable[[], ScaffoldAPI],
    spec: CampaignSpec,
    store: ResultStore,
) -> CampaignSummary:
    """Run a serial, resumable campaign with per-case error isolation."""
    started_at = datetime.now(timezone.utc).isoformat()
    info = pack.info()
    cases: Iterable[BenchmarkCase] = pack.iter_cases(spec.selection)
    if spec.max_cases is not None:
        cases = islice(cases, spec.max_cases)
    selected = list(cases)
    summary = CampaignSummary(
        campaign_id=spec.campaign_id,
        selected_cases=len(selected),
        planned_runs=len(selected) * len(spec.seeds) * spec.repetitions,
    )
    completed = store.completed_run_ids()
    store.write_manifest(
        {
            "campaign": spec.to_dict(),
            "benchmark": info.to_dict(),
            "status": "running",
            "started_at": started_at,
        }
    )
    suite_counts: Counter[str] = Counter()
    variant_counts: Counter[str] = Counter()

    for case in selected:
        for seed in spec.seeds:
            for repetition in range(spec.repetitions):
                run_id = stable_run_id(
                    pack,
                    case,
                    seed=seed,
                    repetition=repetition,
                    campaign_id=spec.campaign_id,
                )
                if run_id in completed:
                    summary.skipped_runs += 1
                    continue
                base = {
                    "run_id": run_id,
                    "campaign_id": spec.campaign_id,
                    "case_id": case.case_id,
                    "benchmark_id": case.benchmark_id,
                    "benchmark_version": info.version,
                    "suite_id": case.suite_id,
                    "variant": case.variant.to_dict(),
                    "seed": seed,
                    "repetition": repetition,
                }
                try:
                    result = run_case(
                        pack,
                        case,
                        scaffold_factory(),
                        runtime=EpisodeRuntime(spec.max_scaffold_turns),
                        runtime_config={"seed": seed},
                    )
                    record = {
                        **base,
                        "status": "completed",
                        "result": result.to_dict(include_trace=True),
                    }
                except Exception as error:
                    summary.error_runs += 1
                    record = {
                        **base,
                        "status": "error",
                        "error": f"{type(error).__name__}: {error}",
                    }
                store.append(record)
                completed.add(run_id)
                summary.executed_runs += 1
                suite_counts[case.suite_id] += 1
                variant_counts[case.variant.kind.value] += 1

    summary.by_suite = dict(sorted(suite_counts.items()))
    summary.by_variant = dict(sorted(variant_counts.items()))
    store.write_manifest(
        {
            "campaign": spec.to_dict(),
            "benchmark": info.to_dict(),
            "status": "completed",
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary.to_dict(),
        }
    )
    return summary


def traverse(
    adapter: BenchmarkAdapter | NativeBenchmarkPack,
    tasks: Iterable[tuple[Env, TaskDefine]] | Iterable[BenchmarkCase],
    scaffold_factory: Callable[[], ScaffoldAPI],
    *,
    output_path: Optional[str | Path] = None,
    max_tasks: Optional[int] = None,
    runtime_factory: Callable[[], EpisodeRuntime] = EpisodeRuntime,
    runtime_config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Run environment/task pairs and optionally append JSONL records."""
    selected = tasks if max_tasks is None else islice(tasks, max_tasks)
    output = Path(output_path) if output_path is not None else None
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.touch(exist_ok=False)

    summaries: List[Dict[str, Any]] = []
    for item in selected:
        if isinstance(item, BenchmarkCase):
            if not isinstance(adapter, NativeBenchmarkPack):
                raise TypeError("BenchmarkCase traversal requires a NativeBenchmarkPack")
            case: Optional[BenchmarkCase] = item
            env = None
            task = case.task
        else:
            case = None
            env, task = item
        try:
            if case is not None:
                benchmark_run = run_case(
                    adapter,
                    case,
                    scaffold_factory(),
                    runtime=runtime_factory(),
                    runtime_config=runtime_config,
                )
            else:
                benchmark_run = run_task(
                    adapter,
                    env,
                    task,
                    scaffold_factory(),
                    runtime=runtime_factory(),
                    runtime_config=runtime_config,
                )
            evaluation = benchmark_run.evaluation
            summary = {
                "task_id": task.task_id,
                "scenario_id": task.scenario,
                "status": benchmark_run.execution.status,
                "env_steps": benchmark_run.execution.env_steps,
                "scaffold_turns": benchmark_run.execution.scaffold_turns,
                "output": benchmark_run.execution.output,
                "passed": evaluation.passed,
                "metrics": evaluation.metrics,
                "error": benchmark_run.execution.metadata.get("error"),
            }
            if case is not None:
                summary.update(
                    {
                        "case_id": case.case_id,
                        "benchmark_id": case.benchmark_id,
                        "suite_id": case.suite_id,
                        "variant": case.variant.to_dict(),
                    }
                )
            details = benchmark_run.to_dict(include_trace=True)
        except Exception as error:
            summary = {
                "task_id": task.task_id,
                "scenario_id": task.scenario,
                "status": "error",
                "env_steps": 0,
                "scaffold_turns": 0,
                "output": None,
                "passed": False,
                "metrics": {},
                "error": f"{type(error).__name__}: {error}",
            }
            details = {
                "task_id": task.task_id,
                "scenario_id": task.scenario,
                "error": summary["error"],
            }
            if case is not None:
                details.update(case.to_dict())

        summaries.append(summary)
        if output is not None:
            with output.open("a", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(
                        {"summary": summary, "details": details},
                        ensure_ascii=False,
                        default=str,
                    )
                    + "\n"
                )
    return summaries
