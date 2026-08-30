"""Deterministic environment simulation and trace collection."""

import uuid
from typing import Any, Callable, Dict, List, Optional

from ..interfaces import Env
from ..task import ScenarioDefine, TaskDefine
from ..trace.models import Trace
from .state import EnvState
from .tool import (
    ToolCall,
    ToolDefine,
    ToolExecutor,
    ToolResult,
)


class EnvSim:
    """
    The main environment class for Agent-Sim.

    Architecture:
    - Python State Engine: Maintains authoritative environment state
    - Rule-based Tool Runtime: Deterministic tool execution
    - Pluggable Scenarios: Load scenarios via registry
    - Trace System: Records all interactions for analysis

    Core Principle:
    > Provide a reliable, observable environment for agent evaluation.
    """

    def __init__(
        self,
        scenario: ScenarioDefine,
        executor: ToolExecutor,
        init_state: Optional[Callable] = None,
        compile_obs: callable = None,
        tool_filter: Optional[
            Callable[[ToolDefine, Optional[TaskDefine], Optional[str]], bool]
        ] = None,
    ):
        """
        Initialize the simulation with scenario-specific components.

        Args:
            scenario: Scenario definition
            init_state: Function that initializes environment state from a seed
            executor: Registered tool executor
            compile_obs: Optional function that compiles agent observations
            tool_filter: Optional per-agent tool visibility policy
        """
        self.scenario = scenario
        self.init_state = init_state
        self.executor = executor
        self.compile_obs = compile_obs or self._default_compile_obs
        self.tool_filter = tool_filter

        # Environment episode bookkeeping
        self.env_state: Optional[EnvState] = None
        self.current_task: Optional[TaskDefine] = None
        self.instruction: str = ""
        self.env_steps: int = 0
        self.tool_history: List[Dict[str, Any]] = []

        # Trace recording
        self.trace: Optional[Trace] = None

    def build_state(self, task: TaskDefine, seed: int) -> EnvState:
        """Build the authoritative state for an episode.

        Subclasses may override this hook when a benchmark task needs custom
        fixture loading, while retaining the standard reset/trace lifecycle.
        """
        if self.init_state is None:
            raise TypeError("EnvSim requires init_state or a build_state override")
        return self.init_state(task.initial_state, seed)

    def reset(self, task: TaskDefine, seed: int = 42, instruction: str = "") -> Dict[str, Any]:
        """
        Reset the environment for a new episode.

        Args:
            task: Task definition to execute
            seed: Random seed for reproducibility
            instruction: Natural language instruction

        Returns:
            Initial observation for the agent
        """
        if task.scenario != self.scenario.scenario_id:
            raise ValueError(
                f"Task scenario {task.scenario!r} does not match environment "
                f"{self.scenario.scenario_id!r}"
            )
        self.current_task = task
        self.instruction = instruction
        self.env_steps = 0
        self.tool_history = []

        # Initialize authoritative environment state
        self.env_state = self.build_state(task, seed)
        if not isinstance(self.env_state, EnvState):
            raise TypeError("init_state must return EnvState")

        # Start trace recording
        self.trace = Trace(
            scenario_id=self.scenario.scenario_id,
            initial_env_state=self.env_state.to_dict(),
        )
        self.trace.record(
            "environment",
            "reset",
            data={"task_id": task.task_id, "seed": seed, "instruction": instruction},
        )

        # Return initial observation
        observation = self.observe()

        return observation

    def observe(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the current observation for the agent.
        The observation is compiled from environment state by the observation compiler.

        Returns:
            Observation dictionary for the agent
        """
        if self.env_state is None:
            return {"error": "Environment not initialized. Call reset() first."}

        observation = self.compile_obs(self.env_state, self.current_task, agent_id)
        if self.trace is not None:
            self.trace.record(
                "environment",
                "observation",
                actor_id=agent_id,
                data={"observation": observation},
            )
        return observation

    def available_tools(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of available tools for the current task.

        Returns:
            List of tool definitions (excluding forbidden tools)
        """
        all_tools = self.executor.get_available_tools()
        forbidden_tools = set(self.current_task.forbidden_tools) if self.current_task else set()

        # Filter out forbidden tools
        allowed_tools = []
        for tool in all_tools:
            if tool.name in forbidden_tools:
                continue
            if self.tool_filter is not None and not self.tool_filter(
                tool, self.current_task, agent_id
            ):
                continue
            allowed_tools.append(tool.to_dict())

        return allowed_tools

    def call_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        agent_id: str = "default",
        thought: Optional[str] = None,
    ) -> ToolResult:
        """
        Execute a tool call.

        Args:
            tool_name: Name of the tool to call
            args: Tool arguments
            agent_id: ID of the agent making the call (for multi-agent)
            thought: Optional agent reasoning for this step

        Returns:
            ToolResult with success/failure status
        """
        if self.env_state is None:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                arguments=args,
                error="Environment not initialized. Call reset() first.",
            )

        # Check step limit
        if self.env_steps >= self.current_task.max_steps:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                arguments=args,
                error=f"Max steps ({self.current_task.max_steps}) reached.",
            )

        call = ToolCall(
            tool_name=tool_name,
            arguments=args,
            agent_id=agent_id,
            call_id=str(uuid.uuid4())[:8],
        )

        # Rejected calls are still episode actions and therefore belong in the
        # generic trace. Benchmark evaluators may inspect them later.
        tool_definition = self.executor.get_tool_define(tool_name)
        agent_can_use_tool = (
            tool_definition is None
            or self.tool_filter is None
            or self.tool_filter(tool_definition, self.current_task, agent_id)
        )
        if tool_name in self.current_task.forbidden_tools:
            result = ToolResult(
                success=False,
                tool_name=tool_name,
                arguments=args,
                error=f"Tool '{tool_name}' is forbidden for this task.",
            )
        elif not agent_can_use_tool:
            result = ToolResult(
                success=False,
                tool_name=tool_name,
                arguments=args,
                error=f"Tool '{tool_name}' is not available to agent '{agent_id}'.",
            )
        else:
            result = self.executor.execute(self.env_state, call)

        # Record action
        self.env_steps += 1
        history_item = {**call.to_dict(), "result": result.to_dict()}
        self.tool_history.append(history_item)

        if self.trace:
            self.trace.record(
                "environment",
                "tool_call",
                actor_id=agent_id,
                data={
                    "env_step": self.env_steps,
                    "call": call.to_dict(),
                    "thought": thought,
                    "result": result.to_dict(),
                    "env_state_after": self.env_state.to_dict(),
                },
            )

        return result

    def is_done(self) -> bool:
        """Check whether the environment's step budget is exhausted.

        Task completion is benchmark-specific and is intentionally evaluated
        outside the simulation.
        """
        if self.current_task is None:
            return True

        return self.env_steps >= self.current_task.max_steps

    def get_trace(self) -> Optional[Trace]:
        """Get the trace for the current episode."""
        return self.trace

    def get_episode_result(self) -> Dict[str, Any]:
        """Return execution facts without benchmark-specific evaluation."""
        return {
            "env_steps": self.env_steps,
            "max_steps_reached": self.is_done(),
            "tool_calls": list(self.tool_history),
        }

    def end_episode(self):
        """End the current episode and finalize trace."""
        if self.trace is None:
            return
        if self.trace.end_time is not None:
            return

        self.trace.record(
            "environment",
            "episode_end",
            data={"env_steps": self.env_steps},
        )
        self.trace.finish(self.env_state.to_dict() if self.env_state is not None else None)

    def _default_compile_obs(
        self,
        state: EnvState,
        task: TaskDefine,
        agent_id: Optional[str],
    ) -> Dict[str, Any]:
        """Default observation compiler - returns raw state dict."""
        del task, agent_id
        return state.to_dict()
