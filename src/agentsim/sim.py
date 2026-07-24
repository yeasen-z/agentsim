"""Deterministic environment simulation and trace collection."""

import uuid
from typing import Any, Dict, List, Optional

from .core import (
    HiddenState,
    ScenarioDefine,
    TaskDefine,
    ToolCall,
    ToolCallRecord,
    ToolExecutor,
    ToolResult,
    Trace,
)


class EnvSim:
    """
    The main environment class for Agent-Sim.

    Architecture:
    - Python State Engine: Maintains ground truth hidden state
    - Rule-based Tool Runtime: Deterministic tool execution
    - Pluggable Scenarios: Load scenarios via registry
    - Trace System: Records all interactions for analysis

    Core Principle:
    > Provide a reliable, observable environment for agent evaluation.
    """

    def __init__(
        self,
        scenario: ScenarioDefine,
        init_state: callable,
        executor: ToolExecutor,
        compile_obs: callable = None,
    ):
        """
        Initialize the simulation with scenario-specific components.

        Args:
            scenario: Scenario definition
            init_state: Function that initializes hidden state from a seed
            executor: Registered tool executor
            compile_obs: Optional function that compiles agent observations
        """
        self.scenario = scenario
        self.init_state = init_state
        self.executor = executor
        self.compile_obs = compile_obs or self._default_compile_obs

        # Runtime state
        self.hidden_state: Optional[HiddenState] = None
        self.current_task: Optional[TaskDefine] = None
        self.instruction: str = ""
        self.step_count: int = 0
        self.action_history: List[Dict[str, Any]] = []

        # Trace recording
        self.trace: Optional[Trace] = None

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
        self.current_task = task
        self.instruction = instruction
        self.step_count = 0
        self.action_history = []

        # Initialize hidden state
        self.hidden_state = self.init_state(task.initial_state, seed)

        # Start trace recording
        self.trace = Trace(
            scenario_id=self.scenario.scenario_id, initial_state=self.hidden_state.to_dict()
        )

        # Return initial observation
        observation = self.observe()

        return observation

    def observe(self) -> Dict[str, Any]:
        """
        Get the current observation for the agent.
        The observation is compiled from hidden state by the observation compiler.

        Returns:
            Observation dictionary for the agent
        """
        if self.hidden_state is None:
            return {"error": "Environment not initialized. Call reset() first."}

        return self.compile_obs(self.hidden_state, self.current_task)

    def available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available tools for the current task.

        Returns:
            List of tool definitions (excluding forbidden tools)
        """
        all_tools = self.executor.get_available_tools()
        forbidden_tools = set(self.current_task.forbidden_tools) if self.current_task else set()

        # Filter out forbidden tools
        allowed_tools = [t.to_dict() for t in all_tools if t.name not in forbidden_tools]

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
        if self.hidden_state is None:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                arguments=args,
                error="Environment not initialized. Call reset() first.",
            )

        # Check step limit
        if self.step_count >= self.current_task.max_steps:
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
        if tool_name in self.current_task.forbidden_tools:
            result = ToolResult(
                success=False,
                tool_name=tool_name,
                arguments=args,
                error=f"Tool '{tool_name}' is forbidden for this task.",
            )
        else:
            result = self.executor.execute(self.hidden_state, call)

        # Record action
        self.step_count += 1
        self.action_history.append(call.to_dict())

        # Get current observation after action
        observation = self.observe()

        # Record to trace
        tool_record = ToolCallRecord(
            name=tool_name,
            arguments=args,
            result=result.result if hasattr(result, "result") else str(result),
            success=result.success,
            error_message=result.error if hasattr(result, "error") else None,
        )

        if self.trace:
            self.trace.record_step(
                step_number=self.step_count,
                observation=observation,
                thought=thought,
                action=call.to_dict(),
                tool_calls=[tool_record],
                state_snapshot=self.hidden_state.to_dict(),
            )

        return result

    def is_done(self) -> bool:
        """Check whether the environment's step budget is exhausted.

        Task completion is benchmark-specific and is intentionally evaluated
        outside the simulation.
        """
        if self.current_task is None:
            return True

        return self.step_count >= self.current_task.max_steps

    def get_trace(self) -> Optional[Trace]:
        """Get the trace for the current episode."""
        return self.trace

    def get_episode_result(self) -> Dict[str, Any]:
        """Return execution facts without benchmark-specific evaluation."""
        return {
            "steps_taken": self.step_count,
            "max_steps_reached": self.is_done(),
            "tool_calls": list(self.action_history),
        }

    def end_episode(self):
        """End the current episode and finalize trace."""
        if self.trace is None:
            return

        # Evaluation metadata is attached later by a benchmark evaluator.
        self.trace.metadata["total_steps"] = self.step_count
        self.trace.metadata["episode_ended"] = True

    def _default_compile_obs(self, state: HiddenState, task: TaskDefine) -> Dict[str, Any]:
        """Default observation compiler - returns raw state dict."""
        return state.to_dict()
