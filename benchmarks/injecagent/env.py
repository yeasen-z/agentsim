"""InjecAgent environment implementation."""

from __future__ import annotations

import ast
import json
import warnings
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agentsim import (
    EnvSim,
    EnvState,
    ScenarioDefine,
    TaskDefine,
    ToolDefine,
    ToolExecutor,
    ToolRiskLevel,
)

from .data import InjecAgentData, TestCase, ToolSpec

BENCHMARK_ID = "injecagent"
BENCHMARK_VERSION = "v1.0.0"


@dataclass
class InjecAgentState(EnvState):
    """State for InjecAgent environment."""

    tool_responses: Dict[str, Any] = field(default_factory=dict)
    injected: bool = False
    attacker_tool_calls: List[Dict[str, Any]] = field(default_factory=list)

    def clone(self) -> "InjecAgentState":
        return InjecAgentState(
            metadata=dict(self.metadata),
            tool_responses=dict(self.tool_responses),
            injected=self.injected,
            attacker_tool_calls=list(self.attacker_tool_calls),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": dict(self.metadata),
            "tool_responses": dict(self.tool_responses),
            "injected": self.injected,
            "attacker_tool_calls": list(self.attacker_tool_calls),
        }


@dataclass
class InjecAgentTask(TaskDefine):
    """Task definition for InjecAgent."""

    source: Optional[TestCase] = field(default=None, repr=False, compare=False)
    attack_mode: str = "dh"


class InjecAgentEnv(EnvSim):
    """InjecAgent environment with injection capabilities."""

    def __init__(self, data: Optional[InjecAgentData] = None):
        self.data = data or InjecAgentData.load()
        self._current_task: Optional[InjecAgentTask] = None

        scenario = ScenarioDefine(
            scenario_id="injecagent",
            name="InjecAgent Indirect Prompt Injection",
            description="Benchmark for indirect prompt injection attacks on tool-integrated agents.",
            state_schema={},
            tools={"injecagent": list(self.data.tools.keys())},
        )

        executor = self._make_executor()
        super().__init__(
            scenario=scenario,
            init_state=None,
            executor=executor,
            compile_obs=self._compile_observation,
        )

    def _make_executor(self) -> ToolExecutor:
        """Create tool executor with all InjecAgent tools."""
        executor = ToolExecutor()

        for full_name, tool_spec in self.data.tools.items():
            risk_level = self._classify_risk(full_name)
            category = "read" if risk_level == ToolRiskLevel.SAFE else "write"

            def make_tool_call(spec: ToolSpec):
                def call(state: InjecAgentState, **arguments: Any) -> Any:
                    return self._execute_tool(spec, state, arguments)

                return call

            executor.register_tool(
                full_name,
                make_tool_call(tool_spec),
                ToolDefine(
                    name=full_name,
                    description=tool_spec.summary,
                    parameters=self._convert_parameters(tool_spec.parameters),
                    risk_level=risk_level,
                    category=category,
                ),
            )

        return executor

    def _classify_risk(self, tool_name: str) -> ToolRiskLevel:
        """Classify tool risk based on name patterns."""
        risky_patterns = (
            "send",
            "delete",
            "update",
            "create",
            "grant",
            "set",
            "transfer",
            "withdraw",
            "purchase",
            "book",
            "cancel",
        )
        name_lower = tool_name.lower()
        if any(pattern in name_lower for pattern in risky_patterns):
            return ToolRiskLevel.RISKY
        return ToolRiskLevel.SAFE

    def _convert_parameters(self, params: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert InjecAgent parameter format to AgentSim format."""
        properties = {}
        required = []

        for param in params:
            name = param.get("name", "")
            properties[name] = {
                "type": param.get("type", "string"),
                "description": param.get("description", ""),
            }
            if param.get("required", False):
                required.append(name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def _execute_tool(
        self,
        tool_spec: ToolSpec,
        state: InjecAgentState,
        arguments: Dict[str, Any],
    ) -> Any:
        """Execute a tool and return result."""
        full_name = tool_spec.full_name
        result: Any = {"success": True, "message": f"Tool {full_name} executed"}

        if self._current_task and self._current_task.source:
            task = self._current_task.source
            if full_name == task.user_tool:
                result = self._parse_tool_response(task.tool_response)
                state.injected = True
            if full_name in task.attacker_tools:
                state.attacker_tool_calls.append(
                    {"tool_name": full_name, "arguments": dict(arguments)}
                )
                simulated_response = self.data.attacker_response(full_name, arguments)
                if simulated_response is not None:
                    result = self._parse_tool_response(simulated_response)

        state.tool_responses[full_name] = {
            "arguments": dict(arguments),
            "result": result,
        }
        return result

    def _parse_tool_response(self, response: str) -> Any:
        """Parse JSON or Python-literal responses without corrupting text."""
        value = response.strip()
        for _ in range(2):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", SyntaxWarning)
                        parsed = ast.literal_eval(value)
                except (SyntaxError, ValueError):
                    return {"raw_response": value}
            if isinstance(parsed, str) and parsed != value:
                value = parsed.strip()
                continue
            return parsed
        return value

    def fresh(self) -> "InjecAgentEnv":
        return InjecAgentEnv(self.data)

    def build_state(self, task: TaskDefine, seed: int) -> InjecAgentState:
        if not isinstance(task, InjecAgentTask) or task.source is None:
            raise TypeError("InjecAgent environments require InjecAgentTask with source.")

        self._current_task = task

        return InjecAgentState(
            metadata={
                "benchmark": BENCHMARK_ID,
                "version": BENCHMARK_VERSION,
                "case_id": task.source.case_id,
                "attack_mode": task.attack_mode,
                "attack_type": task.source.attack_type,
                "seed": seed,
            }
        )

    def _compile_observation(
        self,
        state: InjecAgentState,
        task: InjecAgentTask,
        agent_id: Optional[str],
    ) -> Dict[str, Any]:
        return {
            "benchmark": BENCHMARK_ID,
            "case_id": task.source.case_id if task.source else None,
            "agent_id": agent_id,
            "hint": "Use the available tools to complete the user's request.",
        }


def list_envs() -> List[InjecAgentEnv]:
    """Return InjecAgent environment."""
    return [InjecAgentEnv()]


def list_tasks(env: EnvSim) -> List[InjecAgentTask]:
    """Return all InjecAgent test cases as tasks."""
    if not isinstance(env, InjecAgentEnv):
        raise TypeError("list_tasks expects an InjecAgentEnv")

    tasks = []
    for case in env.data.dh_cases:
        tasks.append(
            InjecAgentTask(
                task_id=case.case_id,
                scenario="injecagent",
                description=case.user_instruction,
                difficulty="base",
                max_steps=10,
                source=case,
                attack_mode="dh",
            )
        )

    for case in env.data.ds_cases:
        tasks.append(
            InjecAgentTask(
                task_id=case.case_id,
                scenario="injecagent",
                description=case.user_instruction,
                difficulty="base",
                max_steps=10,
                source=case,
                attack_mode="ds",
            )
        )

    return tasks
