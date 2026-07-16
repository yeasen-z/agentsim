"""
TinyAct Emulator - Main Package
"""

__version__ = "0.1.0"
__author__ = "TinyAct Team"

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
    TraceRecorder,
    EpisodeTrace,
    StepRecord,
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
    "TraceRecorder",
    "EpisodeTrace",
    "StepRecord",
    
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
