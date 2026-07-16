"""
TinyAct Emulator - Trace Recorder
Records all interactions for analysis and replay.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json
import time
from datetime import datetime


@dataclass
class StepRecord:
    """Record of a single step in the episode."""
    step_number: int
    timestamp: float
    observation: Dict[str, Any]
    action: Optional[Dict[str, Any]]
    result: Optional[Dict[str, Any]]
    verification: Optional[Dict[str, Any]]
    agent_id: str = "default"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "timestamp": self.timestamp,
            "observation": self.observation,
            "action": self.action,
            "result": self.result,
            "verification": self.verification,
            "agent_id": self.agent_id
        }


@dataclass
class EpisodeTrace:
    """Complete trace of an episode."""
    episode_id: str
    scenario_id: str
    task_id: str
    seed: int
    start_time: float
    end_time: Optional[float] = None
    instruction: str = ""
    steps: List[StepRecord] = field(default_factory=list)
    final_result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        if self.end_time is None:
            return 0.0
        return self.end_time - self.start_time
    
    @property
    def total_steps(self) -> int:
        return len(self.steps)
    
    @property
    def success(self) -> bool:
        if not self.final_result:
            return False
        return self.final_result.get("success", False)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "scenario_id": self.scenario_id,
            "task_id": self.task_id,
            "seed": self.seed,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "instruction": self.instruction,
            "steps": [s.to_dict() for s in self.steps],
            "total_steps": self.total_steps,
            "final_result": self.final_result,
            "metadata": self.metadata,
            "success": self.success
        }
    
    def save_json(self, path: str):
        """Save trace to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_json(cls, path: str) -> "EpisodeTrace":
        """Load trace from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        
        steps = []
        for s in data.get("steps", []):
            steps.append(StepRecord(
                step_number=s["step_number"],
                timestamp=s["timestamp"],
                observation=s["observation"],
                action=s["action"],
                result=s["result"],
                verification=s["verification"],
                agent_id=s.get("agent_id", "default")
            ))
        
        return cls(
            episode_id=data["episode_id"],
            scenario_id=data["scenario_id"],
            task_id=data["task_id"],
            seed=data["seed"],
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            instruction=data.get("instruction", ""),
            steps=steps,
            final_result=data.get("final_result"),
            metadata=data.get("metadata", {})
        )


class TraceRecorder:
    """
    Records and manages episode traces.
    """
    
    def __init__(self):
        self.traces: Dict[str, EpisodeTrace] = {}
        self.current_trace: Optional[EpisodeTrace] = None
    
    def start_episode(
        self,
        episode_id: str,
        scenario_id: str,
        task_id: str,
        seed: int,
        instruction: str = "",
        metadata: Dict[str, Any] = None
    ) -> EpisodeTrace:
        """Start recording a new episode."""
        self.current_trace = EpisodeTrace(
            episode_id=episode_id,
            scenario_id=scenario_id,
            task_id=task_id,
            seed=seed,
            start_time=time.time(),
            instruction=instruction,
            metadata=metadata or {}
        )
        self.traces[episode_id] = self.current_trace
        return self.current_trace
    
    def record_step(
        self,
        step_number: int,
        observation: Dict[str, Any],
        action: Optional[Dict[str, Any]],
        result: Optional[Dict[str, Any]],
        verification: Optional[Dict[str, Any]],
        agent_id: str = "default"
    ):
        """Record a single step in the current episode."""
        if self.current_trace is None:
            raise RuntimeError("No active episode. Call start_episode first.")
        
        step = StepRecord(
            step_number=step_number,
            timestamp=time.time(),
            observation=observation,
            action=action,
            result=result,
            verification=verification,
            agent_id=agent_id
        )
        self.current_trace.steps.append(step)
    
    def end_episode(self, final_result: Dict[str, Any]):
        """End the current episode with final result."""
        if self.current_trace is None:
            raise RuntimeError("No active episode. Call start_episode first.")
        
        self.current_trace.end_time = time.time()
        self.current_trace.final_result = final_result
        self.traces[self.current_trace.episode_id] = self.current_trace
        self.current_trace = None
    
    def get_trace(self, episode_id: str) -> Optional[EpisodeTrace]:
        """Get trace for a specific episode."""
        return self.traces.get(episode_id)
    
    def get_all_traces(self) -> List[EpisodeTrace]:
        """Get all recorded traces."""
        return list(self.traces.values())
    
    def clear(self):
        """Clear all recorded traces."""
        self.traces.clear()
        self.current_trace = None
    
    def export_all(self, path: str):
        """Export all traces to a JSON file."""
        data = {
            "traces": [t.to_dict() for t in self.traces.values()],
            "summary": {
                "total_episodes": len(self.traces),
                "successful": sum(1 for t in self.traces.values() if t.success),
                "failed": sum(1 for t in self.traces.values() if not t.success)
            }
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
