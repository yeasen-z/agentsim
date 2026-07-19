"""
Agent Sim - Core Package

Provides the foundational components for building pluggable simulation environments.
"""

from .interface import (
    AgentEnvironmentAdapter,
    EnvironmentCapability,
    EnvironmentInfo,
    EnvironmentInterface,
    create_environment_adapter,
)
from .registry import Plugin, Registry, get_registry, register, registry
from .state import EntityState, HiddenState
from .task import ScenarioDefinition, SuccessCheck, TaskDefinition
from .tool import ToolCall, ToolDefinition, ToolExecutor, ToolResult, ToolRiskLevel
from .trace import StepRecord, ToolCallRecord, Trace
from .verifier import VerificationResult, Verifier

__all__ = [
    # State
    "HiddenState",
    "EntityState",
    # Tools
    "ToolDefinition",
    "ToolResult",
    "ToolCall",
    "ToolExecutor",
    "ToolRiskLevel",
    # Tasks
    "TaskDefinition",
    "ScenarioDefinition",
    "SuccessCheck",
    # Verification
    "Verifier",
    "VerificationResult",
    # Tracing
    "Trace",
    "StepRecord",
    "ToolCallRecord",
    # Registry & Plugins
    "Registry",
    "Plugin",
    "registry",
    "get_registry",
    "register",
    # Environment Interface
    "EnvironmentInterface",
    "EnvironmentInfo",
    "EnvironmentCapability",
    "AgentEnvironmentAdapter",
    "create_environment_adapter",
]
