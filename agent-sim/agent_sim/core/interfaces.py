"""
Agent-Sim Framework - Standard Interfaces

This module defines the core interfaces that allow Runtime and Agent 
implementations to interact with the agent-sim environment.

Key Design Principles:
1. Environment-Centric: agent-sim provides the environment and monitoring
2. Pluggable Components: Runtime and Agent can be swapped freely
3. Trace as Monitor: Complete recording of all interactions
"""
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable
from dataclasses import dataclass, field


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Observation:
    """Observation from environment to agent."""
    state: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "metadata": self.metadata
        }


@dataclass
class Action:
    """Action from agent to environment."""
    action_type: str  # "call_tool", "return_result", "textual"
    tool_name: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result
        }


@dataclass
class ToolDefinition:
    """Definition of a tool available in the environment."""
    name: str
    description: str
    parameters: Dict[str, Any]
    risk_level: str = "safe"  # safe, moderate, high
    category: str = "general"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "risk_level": self.risk_level,
            "category": self.category
        }


@dataclass
class EnvironmentInfo:
    """Complete information about an environment."""
    scenario_id: str
    scenario_name: str
    description: str
    tools: List[ToolDefinition]
    max_steps: int
    constraints: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "description": self.description,
            "tools": [t.to_dict() for t in self.tools],
            "max_steps": self.max_steps,
            "constraints": self.constraints
        }


@dataclass
class ExecutionResult:
    """Result of a runtime execution."""
    status: str  # success, failed, max_steps, error
    result: Any
    steps_taken: int
    trace_available: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Core Interfaces (Protocols)
# ============================================================================

@runtime_checkable
class EnvironmentInterface(Protocol):
    """
    Interface that environments must expose to Runtimes and Agents.
    
    This is the PRIMARY interface provided by agent-sim framework.
    Implementations include OperationEmulator wrapped with adapters.
    """
    
    def get_info(self) -> EnvironmentInfo:
        """Get complete information about the environment."""
        ...
    
    def get_tools(self) -> List[ToolDefinition]:
        """Get list of tools available to agents."""
        ...
    
    def reset(self, task_id: str, seed: int = 42, instruction: str = "") -> Observation:
        """Reset environment for a new episode."""
        ...
    
    def step(self, action: Action) -> Tuple[Observation, bool, Dict[str, Any]]:
        """
        Execute an action and return new observation.
        
        Returns:
            Tuple of (observation, done, info)
        """
        ...
    
    def get_trace(self) -> Any:
        """
        Get the trace monitor for the current episode.
        
        The trace contains complete records of all interactions.
        Return type is 'Any' to allow different trace implementations.
        """
        ...
    
    def verify(self) -> Dict[str, Any]:
        """
        Verify if the task has been completed successfully.
        
        Returns verification result with success/failure status.
        """
        ...


@runtime_checkable
class AgentInterface(Protocol):
    """
    Interface that Agents must implement to work with agent-sim.
    
    This interface is implemented by external Agent components.
    Examples: LLMAgent, RuleBasedAgent, HumanAgent, etc.
    """
    
    def decide(
        self,
        observation: Observation,
        available_tools: List[ToolDefinition],
        context: Dict[str, Any] = None
    ) -> Action:
        """
        Decide on the next action given the current situation.
        
        Args:
            observation: Current observation from environment
            available_tools: List of tools that can be called
            context: Additional context (e.g., conversation history)
        
        Returns:
            Action to execute
        """
        ...
    
    def reset(self):
        """Reset agent state for a new episode."""
        ...


@runtime_checkable
class RuntimeInterface(Protocol):
    """
    Interface that Runtimes must implement to execute agents in agent-sim.
    
    This interface is implemented by external Runtime components.
    Examples: SingleAgentRuntime, MultiAgentRuntime, RLTrainingRuntime, etc.
    """
    
    def run(
        self,
        env: EnvironmentInterface,
        agent: AgentInterface,
        config: Dict[str, Any] = None
    ) -> ExecutionResult:
        """
        Run an agent in the environment.
        
        Args:
            env: Environment to run in
            agent: Agent to execute
            config: Runtime configuration (max_steps, etc.)
        
        Returns:
            ExecutionResult with status and metadata
        """
        ...


# ============================================================================
# Base Implementations (Optional Helpers)
# ============================================================================

class BaseAgent:
    """
    Optional base class for implementing AgentInterface.
    
    Provides common functionality like state management and context tracking.
    """
    
    def __init__(self, agent_id: str = "agent"):
        self.agent_id = agent_id
        self._context: Dict[str, Any] = {}
        self._history: List[Dict[str, Any]] = []
    
    def reset(self):
        """Reset agent state."""
        self._context = {}
        self._history = []
    
    def add_to_context(self, key: str, value: Any):
        """Add something to agent context."""
        self._context[key] = value
    
    def record_action(self, action: Action):
        """Record an action in history."""
        self._history.append({
            "action": action.to_dict(),
            "timestamp": self._get_timestamp()
        })
    
    @staticmethod
    def _get_timestamp() -> float:
        import time
        return time.time()


class BaseRuntime:
    """
    Optional base class for implementing RuntimeInterface.
    
    Provides common functionality like step counting and result aggregation.
    """
    
    def __init__(self, max_steps: int = 10):
        self.max_steps = max_steps
        self._step_count = 0
        self._action_history: List[Action] = []
    
    def reset(self):
        """Reset runtime state."""
        self._step_count = 0
        self._action_history = []
    
    def record_action(self, action: Action):
        """Record an action."""
        self._action_history.append(action)
        self._step_count += 1
    
    def is_done(self, action: Action, verification: Dict[str, Any]) -> bool:
        """Check if execution should terminate."""
        # Max steps reached
        if self._step_count >= self.max_steps:
            return True
        
        # Agent returned result
        if action.action_type == "return_result":
            return True
        
        # Verification succeeded or failed
        if verification.get("success") or verification.get("failed"):
            return True
        
        return False


# ============================================================================
# Factory Functions
# ============================================================================

def create_observation(state: Dict[str, Any], metadata: Dict[str, Any] = None) -> Observation:
    """Factory function to create observations."""
    return Observation(state=state, metadata=metadata or {})


def create_action(
    action_type: str,
    tool_name: str = None,
    arguments: Dict[str, Any] = None,
    result: str = None
) -> Action:
    """Factory function to create actions."""
    return Action(
        action_type=action_type,
        tool_name=tool_name,
        arguments=arguments or {},
        result=result
    )


def create_tool_definition(
    name: str,
    description: str,
    parameters: Dict[str, Any],
    risk_level: str = "safe",
    category: str = "general"
) -> ToolDefinition:
    """Factory function to create tool definitions."""
    return ToolDefinition(
        name=name,
        description=description,
        parameters=parameters,
        risk_level=risk_level,
        category=category
    )
