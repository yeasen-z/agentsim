"""
TinyAct Emulator - Multi-Agent Package
"""
from .agents import (
    # Roles
    AgentRole,
    
    # Messages and State
    AgentMessage,
    AgentState,
    
    # Base and Concrete Agents
    BaseAgent,
    SingleAgent,
    ManagerAgent,
    WorkerAgent,
    ReviewerAgent,
    
    # Orchestration
    MultiAgentOrchestrator,
    CollaborationResult,
    
    # Factory functions
    create_agent,
    create_orchestrator
)

__all__ = [
    # Roles
    "AgentRole",
    
    # Messages and State
    "AgentMessage",
    "AgentState",
    
    # Agents
    "BaseAgent",
    "SingleAgent",
    "ManagerAgent",
    "WorkerAgent",
    "ReviewerAgent",
    
    # Orchestration
    "MultiAgentOrchestrator",
    "CollaborationResult",
    
    # Factories
    "create_agent",
    "create_orchestrator"
]
