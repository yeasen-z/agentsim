"""Minimal AgentDojo task registry and fixture loader.

The execution pipeline is intentionally not vendored. AgentSim owns execution;
this private module preserves AgentDojo's versioned task registrations and
environment fixture semantics.
"""

from __future__ import annotations

import copy
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Dict, Generic, TypeVar

import yaml
from pydantic import BaseModel
from typing_extensions import Self

from benchmarks.agentdojo._vendor.base_tasks import BaseInjectionTask, BaseUserTask
from benchmarks.agentdojo._vendor.functions_runtime import Function, TaskEnvironment
from benchmarks.agentdojo._vendor.yaml_loader import ImportLoader

BenchmarkVersion = tuple[int, int, int]
Env = TypeVar("Env", bound=TaskEnvironment)
Item = TypeVar("Item")


class InjectionVector(BaseModel):
    description: str
    default: str


def _compatible(items: Dict[str, Dict[BenchmarkVersion, Item]], version: BenchmarkVersion):
    compatible = {}
    for item_id, versions in items.items():
        candidates = [candidate for candidate in versions if candidate <= version]
        if candidates:
            compatible[item_id] = versions[max(candidates)]
    return compatible


class TaskSuite(Generic[Env]):
    def __init__(
        self,
        name: str,
        environment_type: type[Env],
        tools: list[Function],
        data_path: Path | None = None,
        benchmark_version: BenchmarkVersion = (1, 0, 0),
    ):
        self.name = name
        self.environment_type = environment_type
        self.tools = tools
        self.data_path = data_path
        self.benchmark_version = benchmark_version
        self._user_tasks: Dict[str, Dict[BenchmarkVersion, BaseUserTask[Env]]] = defaultdict(
            dict
        )
        self._injection_tasks: Dict[
            str, Dict[BenchmarkVersion, BaseInjectionTask[Env]]
        ] = defaultdict(dict)

    def get_new_version(self, benchmark_version: BenchmarkVersion) -> Self:
        new_suite = copy.deepcopy(self)
        new_suite.benchmark_version = benchmark_version
        return new_suite

    @staticmethod
    def _task_number(task_cls: type, prefix: str) -> int:
        match = re.match(rf"{prefix}(\d+)", task_cls.__name__)
        if not match:
            raise ValueError(f"Expected {prefix}<number>, got {task_cls.__name__}")
        return int(match.group(1))

    def register_user_task(self, task_cls: type[BaseUserTask[Env]]):
        task_id = f"user_task_{self._task_number(task_cls, 'UserTask')}"
        task_cls.ID = task_id
        self._user_tasks[task_id][(1, 0, 0)] = task_cls()
        return task_cls

    def update_user_task(self, benchmark_version: BenchmarkVersion):
        def decorator(task_cls: type[BaseUserTask[Env]]):
            task_id = f"user_task_{self._task_number(task_cls, 'UserTask')}"
            if task_id not in self._user_tasks:
                raise ValueError(f"User task {task_id} not found")
            task_cls.ID = task_id
            self._user_tasks[task_id][benchmark_version] = task_cls()
            return task_cls

        return decorator

    def register_injection_task(self, task_cls: type[BaseInjectionTask[Env]]):
        return self.register_new_injection_task((1, 0, 0), task_cls)

    def register_new_injection_task(
        self,
        benchmark_version: BenchmarkVersion,
        task_cls: type[BaseInjectionTask[Env]],
    ):
        task_id = f"injection_task_{self._task_number(task_cls, 'InjectionTask')}"
        task_cls.ID = task_id
        self._injection_tasks[task_id][benchmark_version] = task_cls()
        return task_cls

    def update_injection_task(self, benchmark_version: BenchmarkVersion, new: bool = False):
        def decorator(task_cls: type[BaseInjectionTask[Env]]):
            task_id = f"injection_task_{self._task_number(task_cls, 'InjectionTask')}"
            if task_id not in self._injection_tasks and not new:
                raise ValueError(f"Injection task {task_id} not found")
            task_cls.ID = task_id
            self._injection_tasks[task_id][benchmark_version] = task_cls()
            return task_cls

        return decorator

    @property
    def user_tasks(self):
        return _compatible(self._user_tasks, self.benchmark_version)

    @property
    def injection_tasks(self):
        return _compatible(self._injection_tasks, self.benchmark_version)

    @lru_cache
    def get_user_task_by_id(self, task_id: str):
        return self.user_tasks[task_id]

    @lru_cache
    def get_injection_task_by_id(self, task_id: str):
        return self.injection_tasks[task_id]

    @lru_cache
    def get_latest_user_task_by_id(
        self, task_id: str, version_upperbound: BenchmarkVersion
    ):
        versions = self._user_tasks[task_id]
        return versions[max(version for version in versions if version < version_upperbound)]

    @lru_cache
    def get_latest_injection_task_by_id(
        self, task_id: str, version_upperbound: BenchmarkVersion
    ):
        versions = self._injection_tasks[task_id]
        return versions[max(version for version in versions if version < version_upperbound)]

    def _data_file(self, filename: str) -> Path:
        if self.data_path is not None:
            return self.data_path / filename
        return Path(__file__).parents[1] / "data" / "suites" / self.name / filename

    def _load_yaml(self, filename: str):
        path = self._data_file(filename)
        with path.open(encoding="utf-8") as handle:
            return yaml.load(handle, ImportLoader)

    def get_injection_vectors(self) -> Dict[str, InjectionVector]:
        return {
            vector_id: InjectionVector.model_validate(value)
            for vector_id, value in self._load_yaml("injection_vectors.yaml").items()
        }

    def get_injection_vector_defaults(self) -> Dict[str, str]:
        return {
            vector_id: vector.default
            for vector_id, vector in self.get_injection_vectors().items()
        }

    def load_and_inject_default_environment(self, injections: Dict[str, str]) -> Env:
        defaults = self.get_injection_vector_defaults()
        unknown = set(injections) - set(defaults)
        if unknown:
            raise ValueError(f"Unknown injection vectors: {sorted(unknown)}")

        path = self._data_file("environment.yaml")
        with path.open(encoding="utf-8") as handle:
            environment_data = yaml.load(handle, ImportLoader)
        rendered = yaml.dump(environment_data, default_flow_style=False).format(
            **dict(defaults, **injections)
        )
        return self.environment_type.model_validate(yaml.safe_load(rendered))
