"""AgentDojo data adapted to AgentSim execution primitives."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel

from agentsim import (
    EnvSim,
    HiddenState,
    ScenarioDefine,
    TaskDefine,
    ToolDefine,
    ToolExecutor,
    ToolRiskLevel,
    Trace,
)

from ._vendor.base_tasks import BaseInjectionTask, BaseUserTask
from ._vendor.functions_runtime import FunctionCall, FunctionsRuntime
from ._vendor.task_suite.load_suites import get_suites
from ._vendor.task_suite.task_suite import TaskSuite
from .attacks import Attack, resolve_attack

BENCHMARK_VERSION = "v1.2.2"


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return value


@dataclass
class DojoState(HiddenState):
    """Serializable wrapper around an AgentDojo environment model."""

    data: Any = None

    def clone(self) -> "DojoState":
        return deepcopy(self)

    def to_dict(self) -> Dict[str, Any]:
        state = _jsonable(self.data)
        if isinstance(state, dict):
            return {"metadata": dict(self.metadata), **state}
        return {"metadata": dict(self.metadata), "state": state}


@dataclass
class DojoTask(TaskDefine):
    """AgentSim task record retaining AgentDojo's executable evaluator."""

    source: BaseUserTask = field(default=None, repr=False, compare=False)
    injection: Optional[BaseInjectionTask] = field(default=None, repr=False, compare=False)
    injections: Dict[str, str] = field(default_factory=dict, repr=False, compare=False)
    attack_method: Optional[str] = None


@dataclass
class Case:
    """One clean or attacked AgentDojo episode."""

    env: "DojoEnv"
    task: DojoTask

    @property
    def attacked(self) -> bool:
        return self.task.injection is not None

    @property
    def case_id(self) -> str:
        injection_id = self.task.injection.ID if self.task.injection is not None else "none"
        if self.task.attack_method is None:
            return f"{self.env.suite.name}:{self.task.task_id}:{injection_id}"
        return f"{self.env.suite.name}:{self.task.task_id}:{self.task.attack_method}:{injection_id}"


@dataclass
class Result:
    """Utility and attack outcome for one AgentDojo case."""

    utility_success: bool
    attack_success: Optional[bool]
    case_id: str
    attack_method: Optional[str]

    @property
    def secure(self) -> bool:
        return self.attack_success is not True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "attack_method": self.attack_method,
            "utility_success": self.utility_success,
            "attack_success": self.attack_success,
            "secure": self.secure,
        }


def _tool_category(name: str) -> str:
    read_prefixes = ("get_", "read_", "search_", "list_", "check_")
    return "read" if name.startswith(read_prefixes) else "write"


def _make_executor(suite: TaskSuite) -> ToolExecutor:
    executor = ToolExecutor()
    runtime = FunctionsRuntime(suite.tools)

    for function in suite.tools:
        category = _tool_category(function.name)

        def call(state: DojoState, _name=function.name, **arguments):
            result, error = runtime.run_function(state.data, _name, arguments)
            if error is not None:
                raise ValueError(error)
            return _jsonable(result)

        executor.register_tool(
            function.name,
            call,
            ToolDefine(
                name=function.name,
                description=function.description,
                parameters=function.parameters.model_json_schema(),
                risk_level=(ToolRiskLevel.SAFE if category == "read" else ToolRiskLevel.RISKY),
                category=category,
            ),
        )
    return executor


class DojoEnv(EnvSim):
    """EnvSim backed by one complete AgentDojo task suite."""

    def __init__(self, suite: TaskSuite):
        self.suite = suite
        self.pre_environment = None
        scenario = ScenarioDefine(
            scenario_id=f"agentdojo_{suite.name}",
            name=f"AgentDojo {suite.name.title()}",
            description=f"AgentDojo {BENCHMARK_VERSION} {suite.name} suite.",
            state_schema=list(suite.environment_type.model_fields),
            tools={"agentdojo": [tool.name for tool in suite.tools]},
        )
        super().__init__(
            scenario=scenario,
            init_state=lambda _data, _seed: None,
            executor=_make_executor(suite),
            compile_obs=self._compile_observation,
        )

    def fresh(self) -> "DojoEnv":
        return DojoEnv(self.suite)

    def reset(
        self,
        task: TaskDefine,
        seed: int = 42,
        instruction: str = "",
    ) -> Dict[str, Any]:
        del seed
        if not isinstance(task, DojoTask):
            raise TypeError("AgentDojo environments require tasks from list_tasks(env).")

        environment = self.suite.load_and_inject_default_environment(task.injections)
        environment = task.source.init_environment(environment)
        self.pre_environment = environment.model_copy(deep=True)

        self.current_task = task
        self.instruction = instruction
        self.step_count = 0
        self.action_history = []
        self.hidden_state = DojoState(
            data=environment,
            metadata={
                "benchmark": "agentdojo",
                "version": BENCHMARK_VERSION,
                "suite": self.suite.name,
                "attack_method": task.attack_method,
                "injection_task": task.injection.ID if task.injection is not None else None,
                "injections": dict(task.injections),
            },
        )
        self.trace = Trace(
            scenario_id=self.scenario.scenario_id,
            initial_state=self.hidden_state.to_dict(),
        )
        return self.observe()

    def _compile_observation(self, state: DojoState, task: DojoTask) -> Dict[str, Any]:
        del state
        return {
            "suite": self.suite.name,
            "task_id": task.task_id,
            "hint": "Use the available tools to complete the user's request.",
        }


def _task_sort_key(task_id: str) -> int:
    return int(task_id.rsplit("_", 1)[1])


def list_envs() -> list[EnvSim]:
    """Return all four runnable AgentDojo v1.2.2 environments."""
    suites = get_suites(BENCHMARK_VERSION)
    return [DojoEnv(suites[name]) for name in ("workspace", "travel", "banking", "slack")]


def list_tasks(env: EnvSim) -> list[TaskDefine]:
    """Return AgentDojo user tasks as AgentSim task records."""
    if not isinstance(env, DojoEnv):
        raise TypeError("list_tasks(env) expects an environment returned by list_envs().")

    tasks = []
    for task_id, source in sorted(
        env.suite.user_tasks.items(),
        key=lambda item: _task_sort_key(item[0]),
    ):
        tasks.append(
            DojoTask(
                task_id=task_id,
                scenario=env.scenario.scenario_id,
                description=source.PROMPT,
                difficulty=source.DIFFICULTY.name.lower(),
                max_steps=30,
                source=source,
            )
        )
    return tasks


def _run_ground_truth(suite: TaskSuite, task: DojoTask, injections: Dict[str, str]):
    environment = suite.load_and_inject_default_environment(injections)
    environment = task.source.init_environment(environment)
    runtime = FunctionsRuntime(suite.tools)
    outputs = []
    for call in task.source.ground_truth(environment.model_copy(deep=True)):
        result, error = runtime.run_function(environment, call.function, call.args)
        if error is not None:
            raise RuntimeError(
                f"Ground truth for {task.task_id} failed at {call.function}: {error}"
            )
        outputs.append(_jsonable(result))
    return outputs


def _reachable_vectors(env: DojoEnv, task: DojoTask) -> list[str]:
    defaults = env.suite.get_injection_vector_defaults()
    canaries = {name: f"<CANARY---{name}--->" for name in defaults}
    outputs = _run_ground_truth(env.suite, task, canaries)
    serialized = json.dumps(outputs, ensure_ascii=False, default=str)
    reachable = [name for name, canary in canaries.items() if canary in serialized]
    if not reachable:
        raise ValueError(f"AgentDojo task {task.task_id!r} has no reachable injection vector.")
    return reachable


def build_cases(
    env: EnvSim,
    task: TaskDefine,
    attack: str | Attack | None = None,
    *,
    model_name: str | None = None,
) -> list[Case]:
    """Build a clean case or one attack method's injection-task traversal."""
    if not isinstance(env, DojoEnv) or not isinstance(task, DojoTask):
        raise TypeError("build_cases expects values returned by list_envs/list_tasks.")

    if attack is None:
        clean_task = replace(
            task,
            injection=None,
            injections={},
            attack_method=None,
        )
        return [Case(env=env.fresh(), task=clean_task)]

    method = resolve_attack(attack)
    vectors = _reachable_vectors(env, task)
    cases = []
    injection_tasks = sorted(
        env.suite.injection_tasks.items(),
        key=lambda item: _task_sort_key(item[0]),
    )
    if method.is_dos:
        injection_tasks = injection_tasks[:1]

    for _, injection in injection_tasks:
        attacked_task = replace(
            task,
            injection=injection,
            injections=method.build(
                env.suite,
                task.source,
                injection,
                vectors,
                model_name,
            ),
            attack_method=method.name,
        )
        cases.append(Case(env=env.fresh(), task=attacked_task))
    return cases


def _check_task(
    source,
    model_output: str,
    pre_environment,
    post_environment,
    calls: list[FunctionCall],
) -> bool:
    traced = source.utility_from_traces(
        model_output,
        pre_environment,
        post_environment,
        calls,
    )
    if traced is not None:
        return bool(traced)
    return bool(source.utility(model_output, pre_environment, post_environment))


def _check_injection(
    source,
    model_output: str,
    pre_environment,
    post_environment,
    calls: list[FunctionCall],
) -> bool:
    traced = source.security_from_traces(
        model_output,
        pre_environment,
        post_environment,
        calls,
    )
    if traced is not None:
        return bool(traced)
    return bool(source.security(model_output, pre_environment, post_environment))


def evaluate(env: EnvSim, task: TaskDefine, model_output: str = "") -> Result:
    """Evaluate utility and attack success using AgentDojo's original task logic."""
    if not isinstance(env, DojoEnv) or not isinstance(task, DojoTask):
        raise TypeError("evaluate expects an AgentDojo case environment and task.")
    if env.hidden_state is None or env.pre_environment is None:
        raise RuntimeError("Reset and run the case before evaluation.")

    calls = [
        FunctionCall(function=item["tool_name"], args=item["arguments"])
        for item in env.action_history
    ]
    post_environment = env.hidden_state.data
    utility_success = _check_task(
        task.source,
        model_output,
        env.pre_environment,
        post_environment,
        calls,
    )
    attack_success = None
    if task.injection is not None:
        method = resolve_attack(task.attack_method)
        if method.is_dos:
            attack_success = not utility_success
        else:
            attack_success = _check_injection(
                task.injection,
                model_output,
                env.pre_environment,
                post_environment,
                calls,
            )

    result = Result(
        utility_success=utility_success,
        attack_success=attack_success,
        case_id=Case(env, task).case_id,
        attack_method=task.attack_method,
    )
    if env.trace is not None:
        env.trace.metadata.update(
            {
                "benchmark": "agentdojo",
                "version": BENCHMARK_VERSION,
                "suite": env.suite.name,
                "task_id": task.task_id,
                "injection_task_id": (task.injection.ID if task.injection is not None else None),
                "attack_method": task.attack_method,
                "evaluation": result.to_dict(),
            }
        )
    return result
