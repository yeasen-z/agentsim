"""
Agent Sim - Environment Interface

Provides a standardized interface for agents to discover and interact with 
simulation environments. This is the main entry point for agents to understand
what tools and capabilities are available in a given scenario.
"""
from typing import Any, Dict, List, Optional, Protocol
from dataclasses import dataclass, field
import json

from .tool import ToolDefinition, ToolExecutor, ToolCall, ToolResult
from .state import HiddenState
from .task import TaskDefinition


@dataclass
class EnvironmentCapability:
    """Describes a capability exposed by the environment."""
    name: str
    type: str  # "tool", "observation", "action_space", etc.
    description: str
    schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "schema": self.schema,
            "metadata": self.metadata
        }


@dataclass
class EnvironmentInfo:
    """Complete information about an environment exposed to agents."""
    scenario_id: str
    scenario_name: str
    description: str
    
    # Available tools
    tools: List[ToolDefinition] = field(default_factory=list)
    
    # Observation schema
    observation_schema: Dict[str, Any] = field(default_factory=dict)
    
    # Action space description
    action_space: Dict[str, Any] = field(default_factory=dict)
    
    # Constraints
    constraints: List[str] = field(default_factory=list)
    max_steps: int = 10
    
    # Additional capabilities
    capabilities: List[EnvironmentCapability] = field(default_factory=list)
    
    # Metadata
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "description": self.description,
            "tools": [t.to_dict() for t in self.tools],
            "observation_schema": self.observation_schema,
            "action_space": self.action_space,
            "constraints": self.constraints,
            "max_steps": self.max_steps,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "version": self.version,
            "tags": self.tags
        }
    
    def to_prompt(self) -> str:
        """Generate a human-readable prompt describing the environment."""
        lines = [
            f"# Environment: {self.scenario_name}",
            f"",
            f"{self.description}",
            f"",
            f"## Available Tools ({len(self.tools)}):",
        ]
        
        for tool in self.tools:
            lines.append(f"  - **{tool.name}**: {tool.description}")
            if tool.parameters:
                params = json.dumps(tool.parameters, indent=2)
                lines.append(f"    Parameters: {params}")
        
        if self.constraints:
            lines.extend([
                "",
                "## Constraints:",
            ])
            for constraint in self.constraints:
                lines.append(f"  - {constraint}")
        
        lines.extend([
            "",
            f"**Maximum Steps:** {self.max_steps}",
        ])
        
        return "\n".join(lines)


class EnvironmentInterface(Protocol):
    """
    Protocol defining the interface that environments must expose to agents.
    
    This allows agents to discover what's available without needing to know
    the internal implementation details of the environment.
    """
    
    def get_environment_info(self) -> EnvironmentInfo:
        """Get complete information about the environment."""
        ...
    
    def get_available_tools(self) -> List[ToolDefinition]:
        """Get list of tools available to the agent."""
        ...
    
    def get_tool_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get definition for a specific tool."""
        ...
    
    def get_observation_schema(self) -> Dict[str, Any]:
        """Get the schema of observations provided by the environment."""
        ...
    
    def call_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> ToolResult:
        """Execute a tool call."""
        ...
    
    def get_observation(self) -> Dict[str, Any]:
        """Get the current observation from the environment."""
        ...
    
    def is_done(self) -> bool:
        """Check if the episode is complete."""
        ...
    
    def get_feedback(self) -> Optional[str]:
        """Get optional feedback after an action (for learning agents)."""
        ...


class AgentEnvironmentAdapter:
    """
    Adapter that wraps an OperationEmulator and exposes it through the
    EnvironmentInterface protocol.
    
    This is the main class that agents should interact with.
    """
    
    def __init__(self, emulator):
        """
        Initialize the adapter with an emulator instance.
        
        Args:
            emulator: OperationEmulator instance
        """
        self.emulator = emulator
        self._info_cache: Optional[EnvironmentInfo] = None
    
    def get_environment_info(self) -> EnvironmentInfo:
        """Get complete information about the environment."""
        if self._info_cache is not None:
            return self._info_cache
        
        # Build environment info from emulator components
        scenario = self.emulator.scenario
        tools = self.emulator.available_tools()
        
        # Convert dict tools back to ToolDefinition objects
        tool_defs = []
        for t in tools:
            if isinstance(t, dict):
                tool_defs.append(ToolDefinition(
                    name=t.get("name", ""),
                    description=t.get("description", ""),
                    parameters=t.get("parameters", {}),
                    risk_level=t.get("risk_level", "safe"),
                    category=t.get("category", "general")
                ))
            elif isinstance(t, ToolDefinition):
                tool_defs.append(t)
        
        self._info_cache = EnvironmentInfo(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            description=scenario.description,
            tools=tool_defs,
            observation_schema=self.get_observation_schema(),
            action_space={
                "type": "tool_calls",
                "description": "Agent can call any of the available tools with appropriate arguments",
                "format": {
                    "tool_name": "string",
                    "arguments": "object"
                }
            },
            constraints=[
                f"Maximum {scenario.tasks[0].max_steps if scenario.tasks else 10} steps per episode",
                "Cannot use forbidden tools (filtered from available tools)",
                "Must complete task within step limit"
            ],
            max_steps=scenario.tasks[0].max_steps if scenario.tasks else 10,
            capabilities=self._discover_capabilities()
        )
        
        return self._info_cache
    
    def get_available_tools(self) -> List[ToolDefinition]:
        """Get list of tools available to the agent."""
        tools = self.emulator.available_tools()
        
        result = []
        for t in tools:
            if isinstance(t, dict):
                result.append(ToolDefinition(
                    name=t.get("name", ""),
                    description=t.get("description", ""),
                    parameters=t.get("parameters", {}),
                    risk_level=t.get("risk_level", "safe"),
                    category=t.get("category", "general")
                ))
            elif isinstance(t, ToolDefinition):
                result.append(t)
        
        return result
    
    def get_tool_definition(self, tool_name: str) -> Optional[ToolDefinition]:
        """Get definition for a specific tool."""
        tools = self.get_available_tools()
        for tool in tools:
            if tool.name == tool_name:
                return tool
        return None
    
    def get_observation_schema(self) -> Dict[str, Any]:
        """Get the schema of observations provided by the environment."""
        # Get a sample observation to infer schema
        observation = self.emulator.observe()
        
        def infer_schema(obj: Any, depth: int = 0) -> Dict[str, Any]:
            if depth > 3:  # Limit recursion depth
                return {"type": "object"}
            
            if isinstance(obj, dict):
                schema = {"type": "object", "properties": {}}
                for key, value in obj.items():
                    schema["properties"][key] = infer_schema(value, depth + 1)
                return schema
            elif isinstance(obj, list):
                if obj:
                    return {
                        "type": "array",
                        "items": infer_schema(obj[0], depth + 1)
                    }
                return {"type": "array"}
            elif isinstance(obj, bool):
                return {"type": "boolean"}
            elif isinstance(obj, int):
                return {"type": "integer"}
            elif isinstance(obj, float):
                return {"type": "number"}
            elif isinstance(obj, str):
                return {"type": "string"}
            else:
                return {"type": "string"}
        
        return infer_schema(observation)
    
    def call_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any],
        agent_id: str = "default"
    ) -> ToolResult:
        """Execute a tool call."""
        return self.emulator.call_tool(tool_name, arguments, agent_id)
    
    def get_observation(self) -> Dict[str, Any]:
        """Get the current observation from the environment."""
        return self.emulator.observe()
    
    def is_done(self) -> bool:
        """Check if the episode is complete."""
        return self.emulator.is_done()
    
    def get_feedback(self) -> Optional[str]:
        """Get optional feedback after an action."""
        # Currently not implemented, but could provide hints for learning agents
        return None
    
    def _discover_capabilities(self) -> List[EnvironmentCapability]:
        """Discover additional capabilities of the environment."""
        capabilities = []
        
        # Check if multi-agent is supported
        if hasattr(self.emulator, 'multi_agent_support'):
            capabilities.append(EnvironmentCapability(
                name="multi_agent",
                type="interaction_pattern",
                description="Environment supports multiple agents collaborating",
                metadata={"max_agents": 10}
            ))
        
        # Check if state persistence is supported
        if hasattr(self.emulator, 'save_state'):
            capabilities.append(EnvironmentCapability(
                name="state_persistence",
                type="utility",
                description="Environment state can be saved and loaded",
                schema={"format": "json"}
            ))
        
        # Check if custom verification is supported
        if hasattr(self.emulator, 'verifier'):
            capabilities.append(EnvironmentCapability(
                name="rule_based_verification",
                type="verification",
                description="Task completion is verified using rule-based checks",
                metadata={"check_types": list(self.emulator.verifier.check_handlers.keys())}
            ))
        
        return capabilities
    
    def reset(self, task: TaskDefinition, seed: int = 42, instruction: str = "") -> Dict[str, Any]:
        """Reset the environment for a new episode."""
        self._info_cache = None  # Invalidate cache
        return self.emulator.reset(task, seed, instruction)
    
    def get_final_result(self) -> Dict[str, Any]:
        """Get the final result of the current episode."""
        return self.emulator.get_final_result()
    
    def get_trace(self):
        """Get the trace for the current episode."""
        return self.emulator.get_trace()


def create_environment_adapter(emulator) -> AgentEnvironmentAdapter:
    """
    Factory function to create an environment adapter.
    
    Args:
        emulator: OperationEmulator instance
        
    Returns:
        AgentEnvironmentAdapter wrapping the emulator
    """
    return AgentEnvironmentAdapter(emulator)
