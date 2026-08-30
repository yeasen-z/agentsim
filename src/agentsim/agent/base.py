"""Agent implementations independent of environment and scaffold state."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from ..interfaces import Action, ActionType
from .state import AgentMessage, AgentRole, AgentState


class BaseAgent(ABC):
    """Base class for agents whose private data lives in ``AgentState``."""

    def __init__(self, agent_id: Optional[str] = None, role: AgentRole = AgentRole.WORKER):
        self.agent_id = agent_id or f"agent_{uuid.uuid4().hex[:6]}"
        self.role = role
        self.state = AgentState(agent_id=self.agent_id, role=role)

    @abstractmethod
    def act(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Action:
        """Return one structured action."""

    def receive(self, message: AgentMessage) -> None:
        self.state.receive(message)

    def reset(self) -> None:
        self.state.reset()

    def context(self) -> Dict[str, Any]:
        return {
            "messages": [message.to_dict() for message in self.state.message_history],
            "private": self.state.context,
        }


class SingleAgent(BaseAgent):
    def __init__(
        self,
        agent_id: str = "agent",
        role: AgentRole = AgentRole.EXECUTOR,
        model_client: Any = None,
        system_prompt: Optional[str] = None,
    ):
        super().__init__(agent_id=agent_id, role=role)
        self.model_client = model_client
        self.system_prompt = system_prompt or "You are a helpful assistant."

    def act(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Action:
        del instruction, observation, available_tools, context
        return Action(ActionType.WAIT, actor_id=self.agent_id)


class ManagerAgent(BaseAgent):
    def __init__(self, agent_id: str = "manager"):
        super().__init__(agent_id=agent_id, role=AgentRole.MANAGER)
        self.workers: List[str] = []
        self.delegated_tasks: Dict[str, Dict[str, Any]] = {}

    def reset(self) -> None:
        super().reset()
        self.delegated_tasks.clear()

    def add_worker(self, worker_id: str) -> None:
        if worker_id not in self.workers:
            self.workers.append(worker_id)

    def delegate_task(
        self,
        worker_id: str,
        subtask: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
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
        context: Optional[Dict[str, Any]] = None,
    ) -> Action:
        del instruction, observation, available_tools, context
        return Action(ActionType.WAIT, actor_id=self.agent_id)


class WorkerAgent(BaseAgent):
    def __init__(self, agent_id: str = "worker", specialty: Optional[str] = None):
        super().__init__(agent_id=agent_id, role=AgentRole.WORKER)
        self.specialty = specialty
        self.assigned_tasks: List[Dict[str, Any]] = []

    def reset(self) -> None:
        super().reset()
        self.assigned_tasks.clear()

    def act(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Action:
        del instruction, observation, available_tools, context
        return Action(ActionType.WAIT, actor_id=self.agent_id)


class ReviewerAgent(BaseAgent):
    def __init__(self, agent_id: str = "reviewer"):
        super().__init__(agent_id=agent_id, role=AgentRole.REVIEWER)

    def review(self, action: Action, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        del action, context
        return True, "approved"

    def act(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Action:
        del instruction, observation, available_tools, context
        return Action(ActionType.WAIT, actor_id=self.agent_id)


def create_agent(agent_type: str, agent_id: Optional[str] = None, **kwargs: Any) -> BaseAgent:
    if agent_type == "single":
        return SingleAgent(
            agent_id=agent_id or "agent",
            model_client=kwargs.get("model_client"),
            system_prompt=kwargs.get("system_prompt"),
        )
    if agent_type == "manager":
        return ManagerAgent(agent_id=agent_id or "manager")
    if agent_type == "reviewer":
        return ReviewerAgent(agent_id=agent_id or "reviewer")
    if agent_type == "worker":
        return WorkerAgent(agent_id=agent_id or "worker", specialty=kwargs.get("specialty"))
    raise ValueError(f"Unknown agent type: {agent_type}")
