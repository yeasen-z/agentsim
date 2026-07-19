"""
Agent Sim - Main Package

A pluggable agent interaction simulation platform for developing and testing
agents of all capabilities in controlled, realistic scenarios.
"""

__version__ = "0.2.0"
__author__ = "Agent Sim Team"

from .agents import (
    HarnessAgent,
    LLMAdapter,
    LLMClient,
    MockLLMClient,
)
from .core import (
    AgentEnvironmentAdapter,
    EntityState,
    EnvironmentCapability,
    EnvironmentInfo,
    # Environment Interface
    EnvironmentInterface,
    HiddenState,
    Plugin,
    # Registry & Plugins
    Registry,
    ScenarioDefinition,
    StepRecord,
    SuccessCheck,
    TaskDefinition,
    ToolCall,
    ToolCallRecord,
    ToolDefinition,
    ToolExecutor,
    ToolResult,
    ToolRiskLevel,
    Trace,
    VerificationResult,
    Verifier,
    create_environment_adapter,
    get_registry,
    register,
    registry,
)
from .emulator import OperationEmulator
from .llm_sim import (
    ContentGenerator,
    FeedbackGenerator,
    InstructionGenerator,
    UserSimulator,
)
from .multi_agent import (
    AgentMessage,
    AgentRole,
    AgentState,
    BaseAgent,
    CollaborationResult,
    ManagerAgent,
    MultiAgentOrchestrator,
    ReviewerAgent,
    SingleAgent,
    WorkerAgent,
    create_agent,
    create_orchestrator,
)

__all__ = [
    # Version
    "__version__",
    # Core Emulator
    "OperationEmulator",
    # Core Components
    "HiddenState",
    "EntityState",
    "ToolDefinition",
    "ToolResult",
    "ToolCall",
    "ToolExecutor",
    "ToolRiskLevel",
    "TaskDefinition",
    "ScenarioDefinition",
    "SuccessCheck",
    "Verifier",
    "VerificationResult",
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
    # Multi-Agent
    "AgentRole",
    "AgentMessage",
    "AgentState",
    "BaseAgent",
    "SingleAgent",
    "ManagerAgent",
    "WorkerAgent",
    "ReviewerAgent",
    "MultiAgentOrchestrator",
    "CollaborationResult",
    "create_agent",
    "create_orchestrator",
    # LLM Simulation
    "InstructionGenerator",
    "ContentGenerator",
    "FeedbackGenerator",
    "UserSimulator",
    # Agent Adapters
    "LLMClient",
    "MockLLMClient",
    "LLMAdapter",
    "HarnessAgent",
]
