"""Private state owned by agents."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentRole(str, Enum):
    MANAGER = "manager"
    WORKER = "worker"
    REVIEWER = "reviewer"
    SPECIALIST = "specialist"
    CRITIC = "critic"
    PLANNER = "planner"
    EXECUTOR = "executor"


@dataclass
class AgentMessage:
    """A directed message delivered by a scaffold."""

    sender_id: str
    recipient_id: str
    content: str
    message_type: str = "text"
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "content": self.content,
            "message_type": self.message_type,
            "metadata": deepcopy(self.metadata),
            "timestamp": self.timestamp,
        }


@dataclass
class AgentState:
    """Private context and memory for exactly one agent."""

    agent_id: str
    role: AgentRole
    status: str = "idle"
    context: Dict[str, Any] = field(default_factory=dict)
    message_history: List[AgentMessage] = field(default_factory=list)

    def reset(self) -> None:
        self.status = "idle"
        self.context.clear()
        self.message_history.clear()

    def receive(self, message: AgentMessage) -> None:
        if message.recipient_id not in {self.agent_id, "*"}:
            raise ValueError(
                f"Message for {message.recipient_id!r} cannot be delivered to {self.agent_id!r}"
            )
        self.message_history.append(message)

    def messages(self, sender_id: Optional[str] = None) -> List[AgentMessage]:
        if sender_id is None:
            return list(self.message_history)
        return [message for message in self.message_history if message.sender_id == sender_id]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "status": self.status,
            "context": deepcopy(self.context),
            "message_history": [message.to_dict() for message in self.message_history],
        }
