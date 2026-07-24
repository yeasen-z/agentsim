"""
TinyAct Emulator - Core State Engine
Maintains the ground truth of the environment.
"""

import copy
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class EntityState:
    """Base class for all entity states."""

    id: str

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EntityState":
        return cls(**data)


@dataclass
class HiddenState:
    """
    The ground truth state that the agent cannot directly access.
    Each scenario will extend this with its own specific fields.
    """

    # Common fields across scenarios
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Scenario-specific state (to be extended)
    entities: Dict[str, List[EntityState]] = field(default_factory=dict)

    def clone(self) -> "HiddenState":
        """Create a deep copy of the state."""
        return copy.deepcopy(self)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to dictionary."""
        return {
            "metadata": self.metadata,
            "entities": {
                k: [e.to_dict() if hasattr(e, "to_dict") else e for e in v]
                for k, v in self.entities.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HiddenState":
        """Deserialize state from dictionary."""
        state = cls(metadata=data.get("metadata", {}))
        state.entities = data.get("entities", {})
        return state

    def save(self, path: str):
        """Save state to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "HiddenState":
        """Load state from JSON file."""
        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)
