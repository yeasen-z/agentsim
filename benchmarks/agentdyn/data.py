"""Immutable records loaded from AgentDyn's normalized benchmark data."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any

import yaml

SUITE_NAMES = ("shopping", "github", "dailylife")


@dataclass(frozen=True)
class ToolCallSpec:
    tool: str
    arguments: dict[str, Any]
    placeholder_arguments: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ToolCallSpec":
        return cls(
            tool=value["tool"],
            arguments=value.get("arguments", {}),
            placeholder_arguments=value.get("placeholder_arguments"),
        )


@dataclass(frozen=True)
class UserTaskSpec:
    id: str
    prompt: str
    difficulty: str
    ground_truth_output: str
    ground_truth: tuple[ToolCallSpec, ...]
    ground_truth_results: tuple[Any, ...]
    ground_truth_errors: tuple[str | None, ...]
    ground_truth_valid: bool
    initial_changes: tuple[dict[str, Any], ...]
    expected_changes: tuple[dict[str, Any], ...]
    reachable_vectors: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "UserTaskSpec":
        return cls(
            id=value["id"],
            prompt=value["prompt"],
            difficulty=value["difficulty"],
            ground_truth_output=value.get("ground_truth_output", ""),
            ground_truth=tuple(ToolCallSpec.from_dict(call) for call in value["ground_truth"]),
            ground_truth_results=tuple(value.get("ground_truth_results", [])),
            ground_truth_errors=tuple(value.get("ground_truth_errors", [])),
            ground_truth_valid=bool(value["ground_truth_valid"]),
            initial_changes=tuple(value.get("initial_changes", [])),
            expected_changes=tuple(value.get("expected_changes", [])),
            reachable_vectors=tuple(value.get("reachable_vectors", [])),
        )


@dataclass(frozen=True)
class InjectionTaskSpec:
    id: str
    goal: str
    difficulty: str
    ground_truth_output: str
    ground_truth: tuple[ToolCallSpec, ...]
    ground_truth_results: tuple[Any, ...]
    ground_truth_errors: tuple[str | None, ...]
    expected_success: bool
    expected_changes: tuple[dict[str, Any], ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "InjectionTaskSpec":
        return cls(
            id=value["id"],
            goal=value["goal"],
            difficulty=value["difficulty"],
            ground_truth_output=value.get("ground_truth_output", ""),
            ground_truth=tuple(ToolCallSpec.from_dict(call) for call in value["ground_truth"]),
            ground_truth_results=tuple(value.get("ground_truth_results", [])),
            ground_truth_errors=tuple(value.get("ground_truth_errors", [])),
            expected_success=bool(value["expected_success"]),
            expected_changes=tuple(value.get("expected_changes", [])),
        )


@dataclass(frozen=True)
class SuiteSpec:
    name: str
    benchmark_version: str
    environment: dict[str, Any]
    injection_vectors: dict[str, dict[str, Any]]
    tools: tuple[dict[str, Any], ...]
    user_tasks: dict[str, UserTaskSpec]
    injection_tasks: dict[str, InjectionTaskSpec]

    def fresh_environment(self) -> dict[str, Any]:
        return deepcopy(self.environment)


@lru_cache(maxsize=len(SUITE_NAMES))
def load_suite(name: str) -> SuiteSpec:
    if name not in SUITE_NAMES:
        raise ValueError(f"Unknown AgentDyn suite: {name!r}")
    resource = files("benchmarks.agentdyn").joinpath("data", name, "suite.json")
    raw = json.loads(resource.read_text(encoding="utf-8"))
    environment = _load_yaml_environment(name)
    injection_vectors = raw["injection_vectors"]
    yaml_vectors = _load_yaml_vectors(name)
    for vector, value in yaml_vectors.items():
        if vector in injection_vectors:
            injection_vectors[vector] = {
                **injection_vectors[vector],
                "default": value.get("default", injection_vectors[vector]["default"]),
            }
    return SuiteSpec(
        name=raw["suite"],
        benchmark_version=raw["benchmark_version"],
        environment=environment,
        injection_vectors=injection_vectors,
        tools=tuple(raw["tools"]),
        user_tasks={task["id"]: UserTaskSpec.from_dict(task) for task in raw["user_tasks"]},
        injection_tasks={
            task["id"]: InjectionTaskSpec.from_dict(task) for task in raw["injection_tasks"]
        },
    )


def _yaml_loader(root: Any) -> type[yaml.SafeLoader]:
    class Loader(yaml.SafeLoader):
        pass

    def include(loader: Loader, node: yaml.Node) -> Any:
        path = root / loader.construct_scalar(node)
        with path.open(encoding="utf-8") as stream:
            return yaml.load(stream, Loader)

    Loader.add_constructor("!include", include)
    return Loader


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value.isoformat()
    return value


def _load_yaml_environment(name: str) -> dict[str, Any]:
    root = files("benchmarks.agentdyn").joinpath("data", name)
    loader = _yaml_loader(root)
    with root.joinpath("environment.yaml").open(encoding="utf-8") as stream:
        value = yaml.load(stream, Loader=loader)
    return _jsonable(value)


def _load_yaml_vectors(name: str) -> dict[str, dict[str, Any]]:
    root = files("benchmarks.agentdyn").joinpath("data", name)
    loader = _yaml_loader(root)
    with root.joinpath("injection_vectors.yaml").open(encoding="utf-8") as stream:
        value = yaml.load(stream, Loader=loader)
    return _jsonable(value)
