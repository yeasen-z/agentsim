"""Mutable orchestration state owned by a scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..agent.state import AgentMessage
from ..interfaces import Action


@dataclass
class ScaffoldState:
    """Scheduling and communication state for one scaffold episode."""

    scaffold_id: str
    status: str = "ready"
    turn_count: int = 0
    env_steps: int = 0
    active_agent_id: Optional[str] = None
    final_output: Any = None
    action_history: List[Action] = field(default_factory=list)
    messages: List[AgentMessage] = field(default_factory=list)
    last_outcomes: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scaffold_id": self.scaffold_id,
            "status": self.status,
            "turn_count": self.turn_count,
            "env_steps": self.env_steps,
            "active_agent_id": self.active_agent_id,
            "final_output": self.final_output,
            "action_history": [action.to_dict() for action in self.action_history],
            "messages": [message.to_dict() for message in self.messages],
            "last_outcomes": self.last_outcomes,
            "metadata": self.metadata,
        }
