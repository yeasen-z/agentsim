"""
TinyAct Emulator - Multi-Agent Package
"""

from .agents import (
    # Messages and State
    AgentMessage,
    # Roles
    AgentRole,
    AgentState,
    # Base and Concrete Agents
    BaseAgent,
    CollaborationResult,
    ManagerAgent,
    # Orchestration
    MultiAgentOrchestrator,
    ReviewerAgent,
    SingleAgent,
    WorkerAgent,
    # Factory functions
    create_agent,
    create_orchestrator,
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
    "create_orchestrator",
]
