"""Append-only tracing across environment, agent, and scaffold layers."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TraceEvent:
    """One immutable fact observed at a layer boundary."""

    sequence: int
    layer: str
    event_type: str
    timestamp: str
    actor_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence": self.sequence,
            "layer": self.layer,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "actor_id": self.actor_id,
            "data": deepcopy(self.data),
        }


@dataclass
class Trace:
    """The append-only record of one complete episode."""

    scenario_id: str
    initial_env_state: Optional[Dict[str, Any]] = None
    start_time: str = field(default_factory=_timestamp)
    end_time: Optional[str] = None
    events: List[TraceEvent] = field(default_factory=list)
    final_env_state: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.initial_env_state = deepcopy(self.initial_env_state)

    def record(
        self,
        layer: str,
        event_type: str,
        *,
        actor_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> TraceEvent:
        """Append and return one trace event."""
        if self.end_time is not None:
            raise RuntimeError("Cannot append events to a finished trace")
        if layer not in {"environment", "agent", "scaffold", "runtime", "benchmark"}:
            raise ValueError(f"Unknown trace layer: {layer}")
        event = TraceEvent(
            sequence=len(self.events) + 1,
            layer=layer,
            event_type=event_type,
            timestamp=_timestamp(),
            actor_id=actor_id,
            data=deepcopy(data or {}),
        )
        self.events.append(event)
        return event

    def finish(self, final_env_state: Optional[Dict[str, Any]] = None) -> None:
        """Finalize the trace once episode execution is complete."""
        if final_env_state is not None:
            self.final_env_state = deepcopy(final_env_state)
        if self.end_time is None:
            self.end_time = _timestamp()

    def events_for(
        self,
        *,
        layer: Optional[str] = None,
        event_type: Optional[str] = None,
        actor_id: Optional[str] = None,
    ) -> List[TraceEvent]:
        """Select events by layer, type, and/or actor."""
        return [
            event
            for event in self.events
            if (layer is None or event.layer == layer)
            and (event_type is None or event.event_type == event_type)
            and (actor_id is None or event.actor_id == actor_id)
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "initial_env_state": deepcopy(self.initial_env_state),
            "final_env_state": deepcopy(self.final_env_state),
            "events": [event.to_dict() for event in self.events],
            "metadata": deepcopy(self.metadata),
        }

    def save_json(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as stream:
            json.dump(self.to_dict(), stream, indent=2, ensure_ascii=False, default=str)
