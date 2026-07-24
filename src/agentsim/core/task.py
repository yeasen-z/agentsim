"""
TinyAct Emulator - Task Definition
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

import yaml


@dataclass
class SuccessCheck:
    """A single success condition check."""

    type: str
    params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SuccessCheck":
        return cls(type=data["type"], params=data.get("params", {}))


@dataclass
class TaskDefine:
    """
    Definition of a task within a scenario.
    """

    task_id: str
    scenario: str

    # Hidden goal (not visible to agent)
    hidden_goal: Dict[str, Any] = field(default_factory=dict)

    # Instruction generation config
    instruction_generator: Dict[str, Any] = field(
        default_factory=lambda: {"type": "llm", "style": "natural_user_request"}
    )

    # Initial state seed
    initial_state: Dict[str, Any] = field(default_factory=dict)

    # Success criteria
    success_checks: List[SuccessCheck] = field(default_factory=list)

    # Forbidden tools for this task
    forbidden_tools: List[str] = field(default_factory=list)

    # Constraints
    max_steps: int = 10

    # Metadata
    description: str = ""
    difficulty: str = "medium"  # easy, medium, hard

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskDefine":
        checks = []
        for c in data.get("success", {}).get("checks", []):
            checks.append(SuccessCheck.from_dict(c))

        return cls(
            task_id=data["task_id"],
            scenario=data["scenario"],
            hidden_goal=data.get("hidden_goal", {}),
            instruction_generator=data.get("instruction_generator", {}),
            initial_state=data.get("initial_state", {}),
            success_checks=checks,
            forbidden_tools=data.get("forbidden", []),
            max_steps=data.get("max_steps", 10),
            description=data.get("description", ""),
            difficulty=data.get("difficulty", "medium"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "scenario": self.scenario,
            "hidden_goal": self.hidden_goal,
            "instruction_generator": self.instruction_generator,
            "initial_state": self.initial_state,
            "success": {
                "checks": [{"type": c.type, "params": c.params} for c in self.success_checks]
            },
            "forbidden": self.forbidden_tools,
            "max_steps": self.max_steps,
            "description": self.description,
            "difficulty": self.difficulty,
        }

    @classmethod
    def from_yaml(cls, path: str) -> "TaskDefine":
        """Load task definition from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)

    def save_yaml(self, path: str):
        """Save task definition to YAML file."""
        with open(path, "w") as f:
            yaml.safe_dump(self.to_dict(), f, default_flow_style=False)


@dataclass
class ScenarioDefine:
    """
    Definition of a scenario containing multiple tasks.
    """

    scenario_id: str
    name: str
    description: str = ""

    # State schema
    state_schema: List[str] = field(default_factory=list)

    # Available tools
    tools: Dict[str, List[str]] = field(default_factory=dict)

    # Task list
    tasks: List[TaskDefine] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScenarioDefine":
        return cls(
            scenario_id=data["scenario_id"],
            name=data["name"],
            description=data.get("description", ""),
            state_schema=data.get("state_schema", []),
            tools=data.get("tools", {}),
            tasks=data.get("tasks", []),
        )

    @classmethod
    def from_yaml(cls, path: str) -> "ScenarioDefine":
        """Load scenario definition from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
