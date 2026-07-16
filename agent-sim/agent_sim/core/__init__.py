"""
Agent Sim - Core Package

Provides the foundational components for building pluggable simulation environments.
"""
from .state import HiddenState, EntityState
from .tool import ToolDefinition, ToolResult, ToolCall, ToolExecutor, ToolRiskLevel
from .task import TaskDefinition, ScenarioDefinition, SuccessCheck
from .verifier import Verifier, VerificationResult
from .trace import Trace, StepRecord, ToolCallRecord
from .registry import (
    Registry, 
    Plugin, 
    registry, 
    get_registry,
    register
)
from .interface import (
    EnvironmentInterface,
    EnvironmentInfo,
    EnvironmentCapability,
    AgentEnvironmentAdapter,
    create_environment_adapter
)

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
