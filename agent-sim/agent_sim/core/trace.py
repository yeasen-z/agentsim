"""
Trace System: The "Black Box" of Agent-Sim.
Records every observation, action, tool call, and state change.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import json


@dataclass
class ToolCallRecord:
    """Records a single tool invocation."""
    name: str
    arguments: Dict[str, Any]
    result: Any
    success: bool
    error_message: Optional[str] = None


@dataclass
class StepRecord:
    """Records a single interaction step (Observation -> Action -> Result)."""
    step_number: int
    timestamp: str
    observation: Any  # What the agent saw
    thought: Optional[str]  # Agent's internal reasoning (if provided)
    action: Optional[str]  # High-level action description
    tool_calls: List[ToolCallRecord] = field(default_factory=list)
    state_snapshot_after: Optional[Dict[str, Any]] = None  # Optional hash or snapshot


@dataclass
class Trace:
    """
    The complete record of an agent session.
    Acts as the ground truth for evaluation and debugging.
    """
    scenario_id: str
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    end_time: Optional[str] = None
    initial_state: Optional[Dict[str, Any]] = None
    steps: List[StepRecord] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def record_step(self, 
                    step_number: int, 
                    observation: Any, 
                    thought: Optional[str], 
                    action: Optional[str],
                    tool_calls: List[ToolCallRecord],
                    state_snapshot: Optional[Dict[str, Any]] = None):
        """Append a new step to the trace."""
        record = StepRecord(
            step_number=step_number,
            timestamp=datetime.now().isoformat(),
            observation=observation,
            thought=thought,
            action=action,
            tool_calls=tool_calls,
            state_snapshot_after=state_snapshot
        )
        self.steps.append(record)

    def get_tool_call_history(self) -> List[ToolCallRecord]:
        """Flatten all tool calls across all steps."""
        history = []
        for step in self.steps:
            history.extend(step.tool_calls)
        return history

    def get_final_observation(self) -> Any:
        """Get the last observation seen by the agent."""
        if not self.steps:
            return self.initial_state
        return self.steps[-1].observation

    def has_state_changed(self, key: str) -> bool:
        """Check if a specific state key changed during execution."""
        if not self.initial_state or not self.steps:
            return False
        
        initial_val = self.initial_state.get(key)
        # Check snapshots if available, otherwise infer from tool results
        for step in self.steps:
            if step.state_snapshot_after:
                current_val = step.state_snapshot_after.get(key)
                if current_val != initial_val:
                    return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize trace for storage or analysis."""
        self.end_time = datetime.now().isoformat()
        return {
            "scenario_id": self.scenario_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "initial_state": self.initial_state,
            "steps": [
                {
                    "step": s.step_number,
                    "time": s.timestamp,
                    "obs": s.observation,
                    "thought": s.thought,
                    "action": s.action,
                    "tools": [
                        {
                            "name": tc.name,
                            "args": tc.arguments,
                            "result": tc.result,
                            "success": tc.success
                        } for tc in s.tool_calls
                    ]
                } for s in self.steps
            ],
            "metadata": self.metadata
        }

    def save_json(self, filepath: str):
        """Save trace to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
