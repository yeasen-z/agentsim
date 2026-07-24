"""
TinyAct Emulator - Multi-Agent Framework
Supports both single-agent and multi-agent interaction patterns.
"""

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class AgentRole(Enum):
    """Predefined agent roles for multi-agent scenarios."""

    MANAGER = "manager"
    WORKER = "worker"
    REVIEWER = "reviewer"
    SPECIALIST = "specialist"
    CRITIC = "critic"
    PLANNER = "planner"
    EXECUTOR = "executor"


@dataclass
class AgentMessage:
    """Message passed between agents or from agent to environment."""

    sender_id: str
    content: str
    message_type: str = "text"  # text, tool_call, observation, feedback
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender_id": self.sender_id,
            "content": self.content,
            "message_type": self.message_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


@dataclass
class AgentState:
    """Internal state of an agent."""

    agent_id: str
    role: AgentRole
    status: str = "idle"  # idle, thinking, acting, waiting
    context: Dict[str, Any] = field(default_factory=dict)
    message_history: List[AgentMessage] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "status": self.status,
            "context": self.context,
            "message_count": len(self.message_history),
        }


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    Both single-agent and multi-agent implementations inherit from this.
    """

    def __init__(self, agent_id: str = None, role: AgentRole = AgentRole.WORKER):
        self.agent_id = agent_id or f"agent_{uuid.uuid4().hex[:6]}"
        self.role = role
        self.state = AgentState(agent_id=self.agent_id, role=role)

    @abstractmethod
    def act(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Dict[str, Any] = None,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Decide on an action given the current situation.

        Args:
            instruction: Task instruction
            observation: Current environment observation
            available_tools: List of available tools
            context: Additional context (e.g., messages from other agents)

        Returns:
            Tuple of (tool_name, arguments) or (None, None) for no-op/finish
        """
        pass

    def process_message(self, message: AgentMessage):
        """Process a message from another agent or the environment."""
        message.timestamp = time.time()
        self.state.message_history.append(message)

    def reset(self):
        """Reset agent state."""
        self.state.status = "idle"
        self.state.context = {}
        self.state.message_history = []

    def get_context(self) -> Dict[str, Any]:
        """Get accumulated context from messages."""
        return {
            "messages": [m.to_dict() for m in self.state.message_history],
            "custom": self.state.context,
        }


class SingleAgent(BaseAgent):
    """
    Single agent implementation for standard single-agent scenarios.
    This is the default agent type.
    """

    def __init__(
        self,
        agent_id: str = "single_agent",
        role: AgentRole = AgentRole.EXECUTOR,
        model_client: Any = None,
        system_prompt: str = None,
    ):
        super().__init__(agent_id=agent_id, role=role)
        self.model_client = model_client
        self.system_prompt = system_prompt or "You are a helpful assistant."

    def act(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Dict[str, Any] = None,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Single agent decides and acts independently.

        For LLM-based agents, this would call the model.
        For rule-based agents, this would apply rules.
        """
        self.state.status = "thinking"

        # Default implementation returns None (no-op)
        # Subclasses should override with actual logic

        self.state.status = "idle"
        return None, None


class ManagerAgent(BaseAgent):
    """
    Manager agent that coordinates workers.
    Can delegate tasks and aggregate results.
    """

    def __init__(self, agent_id: str = "manager"):
        super().__init__(agent_id=agent_id, role=AgentRole.MANAGER)
        self.workers: List[str] = []
        self.delegated_tasks: Dict[str, Dict[str, Any]] = {}

    def add_worker(self, worker_id: str):
        """Register a worker agent."""
        self.workers.append(worker_id)

    def delegate_task(self, worker_id: str, subtask: str, context: Dict[str, Any] = None):
        """Delegate a subtask to a worker."""
        task_id = f"task_{uuid.uuid4().hex[:6]}"
        self.delegated_tasks[task_id] = {
            "worker_id": worker_id,
            "subtask": subtask,
            "context": context or {},
            "status": "pending",
            "result": None,
        }
        return task_id

    def act(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Dict[str, Any] = None,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Manager decides: delegate, aggregate, or act directly."""
        self.state.status = "thinking"
        # Implementation depends on specific use case
        self.state.status = "idle"
        return None, None


class WorkerAgent(BaseAgent):
    """
    Worker agent that executes specific tasks.
    Receives delegated tasks from manager.
    """

    def __init__(self, agent_id: str = "worker", specialty: str = None):
        super().__init__(agent_id=agent_id, role=AgentRole.WORKER)
        self.specialty = specialty
        self.assigned_tasks: List[Dict[str, Any]] = []

    def assign_task(self, task: Dict[str, Any]):
        """Receive a task assignment."""
        self.assigned_tasks.append(task)

    def act(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Dict[str, Any] = None,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Worker executes assigned task."""
        self.state.status = "thinking"
        # Implementation depends on specific use case
        self.state.status = "idle"
        return None, None


class ReviewerAgent(BaseAgent):
    """
    Reviewer agent that validates actions before execution.
    Provides safety checking and quality assurance.
    """

    def __init__(self, agent_id: str = "reviewer"):
        super().__init__(agent_id=agent_id, role=AgentRole.REVIEWER)
        self.review_criteria: List[Dict[str, Any]] = []

    def add_criterion(self, criterion: Dict[str, Any]):
        """Add a review criterion."""
        self.review_criteria.append(criterion)

    def review(
        self,
        proposed_action: Tuple[Optional[str], Optional[Dict[str, Any]]],
        context: Dict[str, Any] = None,
    ) -> Tuple[bool, str]:
        """
        Review a proposed action.

        Returns:
            Tuple of (approved, reason)
        """
        # Default: approve all
        return True, "No issues found."

    def act(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Dict[str, Any] = None,
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Reviewer typically doesn't act directly."""
        return None, None


@dataclass
class CollaborationResult:
    """Result of multi-agent collaboration."""

    success: bool
    tool_name: Optional[str]
    arguments: Optional[Dict[str, Any]]
    contributing_agents: List[str]
    discussion_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "contributing_agents": self.contributing_agents,
            "discussion_summary": self.discussion_summary,
        }


class MultiAgentOrchestrator:
    """
    Orchestrates multi-agent collaboration.
    Supports different collaboration modes.
    """

    def __init__(self, mode: str = "sequential"):
        """
        Initialize orchestrator.

        Args:
            mode: Collaboration mode
                - "sequential": Agents take turns in order
                - "hierarchical": Manager delegates to workers
                - "debate": Agents discuss and vote
                - "broadcast": All agents see everything, anyone can act
        """
        self.mode = mode
        self.agents: Dict[str, BaseAgent] = {}
        self.current_turn: int = 0
        self.message_queue: List[AgentMessage] = []

    def add_agent(self, agent: BaseAgent):
        """Add an agent to the orchestration."""
        self.agents[agent.agent_id] = agent

    def remove_agent(self, agent_id: str):
        """Remove an agent from the orchestration."""
        if agent_id in self.agents:
            del self.agents[agent_id]

    def get_agents(self) -> List[BaseAgent]:
        """Get all agents."""
        return list(self.agents.values())

    def select_next_agent(self) -> Optional[BaseAgent]:
        """Select which agent should act next based on mode."""
        if not self.agents:
            return None

        agents_list = list(self.agents.values())

        if self.mode == "sequential":
            # Round-robin
            agent = agents_list[self.current_turn % len(agents_list)]
            self.current_turn += 1
            return agent

        elif self.mode == "hierarchical":
            # Manager always goes first, then workers
            manager = next((a for a in agents_list if a.role == AgentRole.MANAGER), None)
            if manager and self.current_turn == 0:
                return manager
            # Then cycle through workers
            workers = [a for a in agents_list if a.role == AgentRole.WORKER]
            if workers:
                agent = workers[self.current_turn % len(workers)]
                self.current_turn += 1
                return agent
            return manager

        elif self.mode == "debate":
            # All agents participate in discussion, then manager decides
            return agents_list[self.current_turn % len(agents_list)]

        elif self.mode == "broadcast":
            # First available agent acts
            for agent in agents_list:
                if agent.state.status == "idle":
                    return agent
            return agents_list[0]

        return agents_list[0]

    def broadcast_message(self, message: AgentMessage):
        """Broadcast a message to all agents."""
        for agent in self.agents.values():
            agent.process_message(message)
        self.message_queue.append(message)

    def reset(self):
        """Reset orchestrator state."""
        self.current_turn = 0
        self.message_queue = []
        for agent in self.agents.values():
            agent.reset()

    def run_collaboration(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        max_rounds: int = 5,
    ) -> CollaborationResult:
        """
        Run a multi-agent collaboration session.

        Args:
            instruction: Task instruction
            observation: Environment observation
            available_tools: Available tools
            max_rounds: Maximum collaboration rounds

        Returns:
            CollaborationResult with final decision
        """
        contributing_agents = []
        discussion = []

        for _round_num in range(max_rounds):
            agent = self.select_next_agent()
            if not agent:
                break

            context = agent.get_context()
            tool_name, args = agent.act(
                instruction=instruction,
                observation=observation,
                available_tools=available_tools,
                context=context,
            )

            if tool_name:
                contributing_agents.append(agent.agent_id)

                # If reviewer exists, let it review
                reviewer = next(
                    (a for a in self.agents.values() if a.role == AgentRole.REVIEWER), None
                )
                if reviewer:
                    approved, reason = reviewer.review((tool_name, args), context)
                    if not approved:
                        discussion.append(
                            f"Agent {agent.agent_id} proposed {tool_name}, but reviewer rejected: {reason}"
                        )
                        continue

                return CollaborationResult(
                    success=True,
                    tool_name=tool_name,
                    arguments=args,
                    contributing_agents=contributing_agents,
                    discussion_summary="; ".join(discussion),
                )

            discussion.append(f"Agent {agent.agent_id} passed.")

        return CollaborationResult(
            success=False,
            tool_name=None,
            arguments=None,
            contributing_agents=contributing_agents,
            discussion_summary="; ".join(discussion),
        )


def create_agent(agent_type: str, agent_id: str = None, **kwargs) -> BaseAgent:
    """
    Factory function to create agents.

    Args:
        agent_type: Type of agent ("single", "manager", "worker", "reviewer", etc.)
        agent_id: Optional agent ID
        **kwargs: Additional arguments for specific agent types

    Returns:
        Configured agent instance
    """
    if agent_type == "single":
        return SingleAgent(
            agent_id=agent_id,
            model_client=kwargs.get("model_client"),
            system_prompt=kwargs.get("system_prompt"),
        )

    role_map = {"manager": ManagerAgent, "worker": WorkerAgent, "reviewer": ReviewerAgent}

    agent_class = role_map.get(agent_type, WorkerAgent)
    return agent_class(agent_id=agent_id)


def create_orchestrator(
    mode: str = "sequential", agents: List[BaseAgent] = None
) -> MultiAgentOrchestrator:
    """
    Factory function to create orchestrator.

    Args:
        mode: Collaboration mode
        agents: Optional list of agents to add

    Returns:
        Configured orchestrator
    """
    orchestrator = MultiAgentOrchestrator(mode=mode)
    if agents:
        for agent in agents:
            orchestrator.add_agent(agent)
    return orchestrator
