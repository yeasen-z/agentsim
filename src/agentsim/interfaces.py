"""Canonical public interfaces for Agent Sim.

The protocols in this module describe the real execution path used by
``EnvSim`` and ``EnvAdapter``. Environment execution
and trace collection live here; benchmark evaluation remains outside the
framework.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union, runtime_checkable

from .env.tool import ToolDefine, ToolResult, ToolRiskLevel
from .task import TaskDefine


class ActionType(str, Enum):
    """Actions an agent can emit through a scaffold."""

    CALL_TOOL = "call_tool"
    RETURN = "return"
    MESSAGE = "message"
    THINK = "think"
    WAIT = "wait"


@dataclass
class Action:
    """One structured action emitted by an agent."""

    action_type: ActionType
    actor_id: str
    tool_name: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)
    output: Optional[str] = None
    recipient_id: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.action_type, str):
            self.action_type = ActionType(self.action_type)
        if not self.actor_id:
            raise ValueError("Action.actor_id must not be empty")
        if not isinstance(self.arguments, dict):
            raise TypeError("Action.arguments must be a dictionary")
        if not isinstance(self.metadata, dict):
            raise TypeError("Action.metadata must be a dictionary")
        if self.action_type is ActionType.CALL_TOOL and not self.tool_name:
            raise ValueError("call_tool actions require tool_name")
        if self.action_type is ActionType.MESSAGE and not self.recipient_id:
            raise ValueError("message actions require recipient_id")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "actor_id": self.actor_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "output": self.output,
            "recipient_id": self.recipient_id,
            "content": self.content,
            "metadata": self.metadata,
        }


@dataclass
class RunResult:
    """Complete execution facts returned before benchmark evaluation."""

    status: str
    output: Any
    env_steps: int
    scaffold_turns: int
    actions: List[Action] = field(default_factory=list)
    trace: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "output": self.output,
            "env_steps": self.env_steps,
            "scaffold_turns": self.scaffold_turns,
            "actions": [action.to_dict() for action in self.actions],
            "trace": self.trace.to_dict() if self.trace is not None else None,
            "metadata": self.metadata,
        }


@dataclass
class EnvCapability:
    """A capability exposed by an environment."""

    name: str
    type: str
    description: str
    schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "schema": self.schema,
            "metadata": self.metadata,
        }


@dataclass
class EnvInfo:
    """Agent-facing metadata about one simulation environment."""

    scenario_id: str
    scenario_name: str
    description: str
    tools: List[ToolDefine] = field(default_factory=list)
    observation_schema: Dict[str, Any] = field(default_factory=dict)
    action_space: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    max_steps: int = 10
    capabilities: List[EnvCapability] = field(default_factory=list)
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "description": self.description,
            "tools": [tool.to_dict() for tool in self.tools],
            "observation_schema": self.observation_schema,
            "action_space": self.action_space,
            "constraints": self.constraints,
            "max_steps": self.max_steps,
            "capabilities": [capability.to_dict() for capability in self.capabilities],
            "version": self.version,
            "tags": self.tags,
        }

    def to_prompt(self) -> str:
        """Render environment metadata as an agent-readable prompt."""
        lines = [
            f"# Environment: {self.scenario_name}",
            "",
            self.description,
            "",
            f"## Available Tools ({len(self.tools)}):",
        ]
        for tool in self.tools:
            lines.append(f"  - **{tool.name}**: {tool.description}")
            if tool.parameters:
                lines.append(f"    Parameters: {json.dumps(tool.parameters, indent=2)}")
        if self.constraints:
            lines.extend(["", "## Constraints:"])
            lines.extend(f"  - {constraint}" for constraint in self.constraints)
        lines.extend(["", f"**Maximum Steps:** {self.max_steps}"])
        return "\n".join(lines)


@runtime_checkable
class Env(Protocol):
    """The single environment contract exposed to runtimes and agents."""

    def info(self) -> EnvInfo: ...

    def tools(self, agent_id: Optional[str] = None) -> List[ToolDefine]: ...

    def tool(self, name: str, agent_id: Optional[str] = None) -> Optional[ToolDefine]: ...

    def schema(self, agent_id: Optional[str] = None) -> Dict[str, Any]: ...

    def reset(self, task: TaskDefine, seed: int = 42, instruction: str = "") -> Dict[str, Any]: ...

    def observe(self, agent_id: Optional[str] = None) -> Dict[str, Any]: ...

    def call(self, name: str, args: Dict[str, Any], agent_id: str = "default") -> ToolResult: ...

    def done(self) -> bool: ...

    def result(self) -> Dict[str, Any]: ...

    def trace(self) -> Any: ...

    def finish(self) -> None: ...


@runtime_checkable
class AgentAPI(Protocol):
    """The contract implemented by an Agent Sim-compatible agent."""

    agent_id: str
    state: Any

    def act(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Action: ...

    def reset(self) -> None: ...

    def receive(self, message: Any) -> None: ...

    def context(self) -> Dict[str, Any]: ...


@runtime_checkable
class ScaffoldAPI(Protocol):
    """The contract for coordinating one or more agents."""

    scaffold_id: str
    state: Any

    def reset(self) -> None: ...

    def select_actor(self) -> Optional[str]: ...

    def act(
        self,
        actor_id: str,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
    ) -> Action: ...

    def apply(self, action: Action, outcome: Any = None) -> None: ...

    def done(self) -> bool: ...

    def output(self) -> Any: ...


@runtime_checkable
class RuntimeAPI(Protocol):
    """The contract for executing a scaffold against an environment."""

    def run(
        self,
        env: Env,
        scaffold: ScaffoldAPI,
        task: TaskDefine,
        instruction: str = "",
        config: Optional[Dict[str, Any]] = None,
    ) -> RunResult: ...


class EnvAdapter:
    """Expose an ``EnvSim`` through ``Env``."""

    def __init__(self, sim: Any):
        self.sim = sim
        self._info_cache: Optional[EnvInfo] = None

    @staticmethod
    def _as_tool_define(raw: Union[ToolDefine, Dict[str, Any]]) -> ToolDefine:
        if isinstance(raw, ToolDefine):
            return raw

        risk_level = raw.get("risk_level", ToolRiskLevel.SAFE)
        if isinstance(risk_level, str):
            risk_level = ToolRiskLevel(risk_level)
        return ToolDefine(
            name=raw.get("name", ""),
            description=raw.get("description", ""),
            parameters=raw.get("parameters", {}),
            risk_level=risk_level,
            category=raw.get("category", "general"),
        )

    def info(self) -> EnvInfo:
        if self._info_cache is not None:
            return self._info_cache

        scenario = self.sim.scenario
        task = self.sim.current_task
        max_steps = task.max_steps if task is not None else 10
        self._info_cache = EnvInfo(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            description=scenario.description,
            tools=self.tools(),
            observation_schema=self.schema(),
            action_space={
                "type": "tool_calls",
                "description": "Call one available tool with schema-valid arguments.",
                "format": {"tool_name": "string", "arguments": "object"},
            },
            constraints=[
                f"Maximum {max_steps} steps per episode",
                "Forbidden tools are omitted from the available tool list",
            ],
            max_steps=max_steps,
            capabilities=self._discover_capabilities(),
        )
        return self._info_cache

    def tools(self, agent_id: Optional[str] = None) -> List[ToolDefine]:
        return [self._as_tool_define(tool) for tool in self.sim.available_tools(agent_id)]

    def tool(self, name: str, agent_id: Optional[str] = None) -> Optional[ToolDefine]:
        return next(
            (tool for tool in self.tools(agent_id) if tool.name == name),
            None,
        )

    def schema(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        def infer_schema(value: Any, depth: int = 0) -> Dict[str, Any]:
            if depth > 3:
                return {"type": "object"}
            if isinstance(value, dict):
                return {
                    "type": "object",
                    "properties": {
                        key: infer_schema(item, depth + 1) for key, item in value.items()
                    },
                }
            if isinstance(value, list):
                schema = {"type": "array"}
                if value:
                    schema["items"] = infer_schema(value[0], depth + 1)
                return schema
            if isinstance(value, bool):
                return {"type": "boolean"}
            if isinstance(value, int):
                return {"type": "integer"}
            if isinstance(value, float):
                return {"type": "number"}
            if isinstance(value, str):
                return {"type": "string"}
            return {"type": "object"}

        return infer_schema(self.observe(agent_id))

    def reset(self, task: TaskDefine, seed: int = 42, instruction: str = "") -> Dict[str, Any]:
        observation = self.sim.reset(task, seed, instruction)
        self._info_cache = None
        return observation

    def observe(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        return self.sim.observe(agent_id)

    def call(self, name: str, args: Dict[str, Any], agent_id: str = "default") -> ToolResult:
        return self.sim.call_tool(name, args, agent_id)

    def done(self) -> bool:
        return self.sim.is_done()

    def result(self) -> Dict[str, Any]:
        return self.sim.get_episode_result()

    def trace(self) -> Any:
        return self.sim.get_trace()

    def finish(self) -> None:
        self.sim.end_episode()

    def _discover_capabilities(self) -> List[EnvCapability]:
        capabilities = [
            EnvCapability(
                name="agent_scoped_views",
                type="interaction_pattern",
                description="Observations and tool visibility can be scoped by agent ID.",
            )
        ]
        if hasattr(self.sim, "save_state"):
            capabilities.append(
                EnvCapability(
                    name="state_persistence",
                    type="utility",
                    description="Environment state can be saved and loaded.",
                    schema={"format": "json"},
                )
            )
        return capabilities


def as_env(sim: Any) -> EnvAdapter:
    """Wrap an ``EnvSim`` with the canonical ``Env`` API."""
    return EnvAdapter(sim)


def create_action(
    action_type: Union[ActionType, str],
    actor_id: str,
    tool_name: Optional[str] = None,
    arguments: Optional[Dict[str, Any]] = None,
    output: Optional[str] = None,
    recipient_id: Optional[str] = None,
    content: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Action:
    return Action(
        action_type=action_type,
        actor_id=actor_id,
        tool_name=tool_name,
        arguments=arguments or {},
        output=output,
        recipient_id=recipient_id,
        content=content,
        metadata=metadata or {},
    )


def define_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any],
    risk_level: Union[ToolRiskLevel, str] = ToolRiskLevel.SAFE,
    category: str = "general",
) -> ToolDefine:
    """Create the same ``ToolDefine`` used by ``ToolExecutor``."""
    if isinstance(risk_level, str):
        risk_level = ToolRiskLevel(risk_level)
    return ToolDefine(
        name=name,
        description=description,
        parameters=parameters,
        risk_level=risk_level,
        category=category,
    )
