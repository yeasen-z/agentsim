"""
Agent Sim - Main Package

A pluggable agent interaction simulation platform for developing and testing 
agents of all capabilities in controlled, realistic scenarios.
"""

__version__ = "0.2.0"
__author__ = "Agent Sim Team"

from .emulator import OperationEmulator
from .core import (
    HiddenState,
    EntityState,
    ToolDefinition,
    ToolResult,
    ToolCall,
    ToolExecutor,
    ToolRiskLevel,
    TaskDefinition,
    ScenarioDefinition,
    SuccessCheck,
    Verifier,
    VerificationResult,
    Trace,
    StepRecord,
    ToolCallRecord,
    # Registry & Plugins
    Registry,
    Plugin,
    registry,
    get_registry,
    register,
    # Environment Interface
    EnvironmentInterface,
    EnvironmentInfo,
    EnvironmentCapability,
    AgentEnvironmentAdapter,
    create_environment_adapter,
)
from .multi_agent import (
    AgentRole,
    AgentMessage,
    AgentState,
    BaseAgent,
    SingleAgent,
    ManagerAgent,
    WorkerAgent,
    ReviewerAgent,
    MultiAgentOrchestrator,
    CollaborationResult,
    create_agent,
    create_orchestrator,
)
from .llm_sim import (
    InstructionGenerator,
    ContentGenerator,
    FeedbackGenerator,
    UserSimulator,
)
from .agents import (
    LLMClient,
    MockLLMClient,
    LLMAdapter,
    HarnessAgent,
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
