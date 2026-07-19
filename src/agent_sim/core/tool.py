"""
TinyAct Emulator - Tool Definitions and Execution Results
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ToolRiskLevel(Enum):
    """Risk level of a tool operation."""

    SAFE = "safe"
    MODERATE = "moderate"
    RISKY = "risky"
    DESTRUCTIVE = "destructive"


@dataclass
class ToolDefinition:
    """Definition of a tool available to agents."""

    name: str
    description: str
    parameters: Dict[str, Any]  # JSON schema-like
    risk_level: ToolRiskLevel = ToolRiskLevel.SAFE
    category: str = "general"  # read, write, risky, etc.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "risk_level": self.risk_level.value,
            "category": self.category,
        }


@dataclass
class ToolResult:
    """Result of a tool execution."""

    success: bool
    tool_name: str
    arguments: Dict[str, Any]
    result: Any = None
    error: Optional[str] = None
    message: str = ""
    state_changed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "error": self.error,
            "message": self.message,
            "state_changed": self.state_changed,
        }


@dataclass
class ToolCall:
    """A tool call request from an agent."""

    tool_name: str
    arguments: Dict[str, Any]
    agent_id: str = "default"  # For multi-agent support
    call_id: str = ""  # Unique identifier for tracing

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "agent_id": self.agent_id,
            "call_id": self.call_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolCall":
        return cls(
            tool_name=data["tool_name"],
            arguments=data.get("arguments", {}),
            agent_id=data.get("agent_id", "default"),
            call_id=data.get("call_id", ""),
        )


class ToolExecutor:
    """
    Executes tools against the environment state.
    Each scenario provides its own tool implementations.
    """

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.definitions: Dict[str, ToolDefinition] = {}

    def register_tool(self, name: str, func: Callable, definition: ToolDefinition):
        """Register a tool implementation."""
        self.tools[name] = func
        self.definitions[name] = definition

    def execute(self, state: Any, call: ToolCall) -> ToolResult:
        """Execute a tool call against the state."""
        if call.tool_name not in self.tools:
            return ToolResult(
                success=False,
                tool_name=call.tool_name,
                arguments=call.arguments,
                error=f"Unknown tool: {call.tool_name}",
                message=f"Tool '{call.tool_name}' not found.",
            )

        try:
            func = self.tools[call.tool_name]
            result = func(state, **call.arguments)

            if isinstance(result, ToolResult):
                return result

            # Wrap raw result in ToolResult
            return ToolResult(
                success=True,
                tool_name=call.tool_name,
                arguments=call.arguments,
                result=result,
                message=f"Tool '{call.tool_name}' executed successfully.",
                state_changed=True,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=call.tool_name,
                arguments=call.arguments,
                error=str(e),
                message=f"Error executing '{call.tool_name}': {str(e)}",
            )

    def get_available_tools(self) -> List[ToolDefinition]:
        """Get all registered tool definitions."""
        return list(self.definitions.values())

    def get_tool_definition(self, name: str) -> Optional[ToolDefinition]:
        """Get definition for a specific tool."""
        return self.definitions.get(name)
