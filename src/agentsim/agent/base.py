"""Agent implementations independent of environment and scaffold state."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..interfaces import Action, ActionType
from .state import AgentMessage, AgentRole, AgentState


class BaseAgent(ABC):
    """Base class for agents whose private data lives in ``AgentState``."""

    def __init__(self, agent_id: Optional[str] = None, role: AgentRole = AgentRole.EXECUTOR):
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


def create_agent(agent_type: str, agent_id: Optional[str] = None, **kwargs: Any) -> BaseAgent:
    if agent_type == "single":
        return SingleAgent(
            agent_id=agent_id or "agent",
            model_client=kwargs.get("model_client"),
            system_prompt=kwargs.get("system_prompt"),
        )
    raise ValueError(f"Unknown agent type: {agent_type}")
