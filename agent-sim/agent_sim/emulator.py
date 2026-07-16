"""
Agent-Sim Emulator - Main Environment Class
Pluggable Agent Interaction Simulation Platform
"""
import uuid
from typing import Any, Dict, List, Optional, Tuple
from .core import (
    HiddenState, TaskDefinition, ScenarioDefinition,
    ToolCall, ToolResult, ToolExecutor,
    Verifier, VerificationResult,
    Trace, StepRecord, ToolCallRecord
)


class OperationEmulator:
    """
    The main environment class for Agent-Sim.
    
    Architecture:
    - Python State Engine: Maintains ground truth hidden state
    - Rule-based Tool Runtime: Deterministic tool execution
    - Rule-based Verifier: Success/failure/risk checking
    - Pluggable Scenarios: Load scenarios via registry
    - Trace System: Records all interactions for analysis
    
    Core Principle: 
    > Provide a reliable, observable environment for agent evaluation.
    """
    
    def __init__(
        self,
        scenario: ScenarioDefinition,
        state_initializer: callable,
        tool_executor: ToolExecutor,
        verifier: Verifier,
        observation_compiler: callable = None
    ):
        """
        Initialize the emulator with scenario-specific components.
        
        Args:
            scenario: Scenario definition
            state_initializer: Function to initialize hidden state from seed
            tool_executor: ToolExecutor with registered tools
            verifier: Verifier for success checking
            observation_compiler: Optional function to compile observation for agent
        """
        self.scenario = scenario
        self.state_initializer = state_initializer
        self.tool_executor = tool_executor
        self.verifier = verifier
        self.observation_compiler = observation_compiler or self._default_observation_compiler
        
        # Runtime state
        self.hidden_state: Optional[HiddenState] = None
        self.current_task: Optional[TaskDefinition] = None
        self.instruction: str = ""
        self.step_count: int = 0
        self.action_history: List[Dict[str, Any]] = []
        
        # Trace recording
        self.trace: Optional[Trace] = None
    
    def reset(
        self, 
        task: TaskDefinition, 
        seed: int = 42,
        instruction: str = ""
    ) -> Dict[str, Any]:
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
        self.hidden_state = self.state_initializer(task.initial_state, seed)
        
        # Start trace recording
        self.trace = Trace(
            scenario_id=self.scenario.scenario_id,
            initial_state=self.hidden_state.to_dict()
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
        
        return self.observation_compiler(self.hidden_state, self.current_task)
    
    def available_tools(self) -> List[Dict[str, Any]]:
        """
        Get list of available tools for the current task.
        
        Returns:
            List of tool definitions (excluding forbidden tools)
        """
        all_tools = self.tool_executor.get_available_tools()
        
        # Filter out forbidden tools
        allowed_tools = [
            t.to_dict() for t in all_tools 
            if t.name not in self.current_task.forbidden_tools
        ]
        
        return allowed_tools
    
    def call_tool(
        self, 
        tool_name: str, 
        args: Dict[str, Any],
        agent_id: str = "default",
        thought: Optional[str] = None
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
                error="Environment not initialized. Call reset() first."
            )
        
        # Check step limit
        if self.step_count >= self.current_task.max_steps:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                arguments=args,
                error=f"Max steps ({self.current_task.max_steps}) reached."
            )
        
        # Check if tool is forbidden
        if tool_name in self.current_task.forbidden_tools:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                arguments=args,
                error=f"Tool '{tool_name}' is forbidden for this task."
            )
        
        # Create tool call
        call = ToolCall(
            tool_name=tool_name,
            arguments=args,
            agent_id=agent_id,
            call_id=str(uuid.uuid4())[:8]
        )
        
        # Execute tool
        result = self.tool_executor.execute(self.hidden_state, call)
        
        # Record action
        self.step_count += 1
        self.action_history.append(call.to_dict())
        
        # Get current observation after action
        observation = self.observe()
        
        # Record to trace
        tool_record = ToolCallRecord(
            name=tool_name,
            arguments=args,
            result=result.result if hasattr(result, 'result') else str(result),
            success=result.success,
            error_message=result.error if hasattr(result, 'error') else None
        )
        
        if self.trace:
            self.trace.record_step(
                step_number=self.step_count,
                observation=observation,
                thought=thought,
                action=call.to_dict(),
                tool_calls=[tool_record],
                state_snapshot=self.hidden_state.to_dict()
            )
        
        return result
    
    def verify(self) -> VerificationResult:
        """
        Check if the task has been completed successfully.
        
        Returns:
            VerificationResult with success/failure status
        """
        if self.hidden_state is None or self.current_task is None:
            return VerificationResult(
                failed=True,
                reason="Environment not initialized. Call reset() first."
            )
        
        return self.verifier.verify(
            state=self.hidden_state,
            task=self.current_task,
            action_history=self.action_history
        )
    
    def is_done(self) -> bool:
        """Check if the episode is complete."""
        if self.current_task is None:
            return True
        
        if self.step_count >= self.current_task.max_steps:
            return True
        
        verification = self.verify()
        return verification.success or verification.failed
    
    def get_trace(self) -> Optional[Trace]:
        """Get the trace for the current episode."""
        return self.trace
    
    def get_final_result(self) -> Dict[str, Any]:
        """Get the final result of the current episode."""
        verification = self.verify()
        return {
            "success": verification.success,
            "failed": verification.failed,
            "reason": verification.reason,
            "steps_taken": self.step_count,
            "checks_passed": verification.checks_passed,
            "checks_failed": verification.checks_failed,
            "risk_violations": verification.risk_violations
        }
    
    def end_episode(self):
        """End the current episode and finalize trace."""
        if self.trace is None:
            return
        
        # Add final verification to metadata
        verification = self.verify()
        self.trace.metadata["final_verification"] = verification.to_dict()
        self.trace.metadata["total_steps"] = self.step_count
    
    def _default_observation_compiler(
        self, 
        state: HiddenState, 
        task: TaskDefinition
    ) -> Dict[str, Any]:
        """Default observation compiler - returns raw state dict."""
        return state.to_dict()
