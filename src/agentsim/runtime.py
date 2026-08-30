"""Execution mechanism connecting scaffolds to environments."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .interfaces import (
    ActionType,
    Env,
    RunResult,
    ScaffoldAPI,
)
from .task import TaskDefine


class EpisodeRuntime:
    """Run a scaffold until it returns, exhausts its budget, or the env ends."""

    def __init__(self, max_scaffold_turns: int = 100):
        if max_scaffold_turns < 1:
            raise ValueError("max_scaffold_turns must be positive")
        self.max_scaffold_turns = max_scaffold_turns

    def run(
        self,
        env: Env,
        scaffold: ScaffoldAPI,
        task: TaskDefine,
        instruction: str = "",
        config: Optional[Dict[str, Any]] = None,
    ) -> RunResult:
        if not isinstance(env, Env):
            raise TypeError("env must implement Env")
        if not isinstance(scaffold, ScaffoldAPI):
            raise TypeError("scaffold must implement ScaffoldAPI")

        config = config or {}
        instruction = instruction or task.description or "Complete the task"
        turn_limit = int(config.get("max_scaffold_turns", self.max_scaffold_turns))
        if turn_limit < 1:
            raise ValueError("max_scaffold_turns must be positive")

        initial_observation = env.reset(
            task,
            seed=int(config.get("seed", 42)),
            instruction=instruction,
        )
        scaffold.reset()
        trace = env.trace()
        trace.record(
            "scaffold",
            "reset",
            data={
                "scaffold_id": scaffold.scaffold_id,
                "state": scaffold.state.to_dict(),
            },
        )

        status = "running"
        error: Optional[str] = None
        try:
            while scaffold.state.turn_count < turn_limit:
                if scaffold.done():
                    status = scaffold.state.status
                    break
                if env.done():
                    status = "environment_exhausted"
                    break

                actor_id = scaffold.select_actor()
                if actor_id is None:
                    status = "no_actor"
                    break
                trace.record(
                    "scaffold",
                    "actor_selected",
                    actor_id=actor_id,
                    data={"turn": scaffold.state.turn_count + 1},
                )

                observation = env.observe(actor_id)
                tools = [tool.to_dict() for tool in env.tools(actor_id)]
                action = scaffold.act(actor_id, instruction, observation, tools)
                trace.record(
                    "agent",
                    "action",
                    actor_id=actor_id,
                    data={"action": action.to_dict()},
                )

                outcome = None
                if action.action_type is ActionType.CALL_TOOL:
                    outcome = env.call(
                        action.tool_name or "",
                        action.arguments,
                        agent_id=actor_id,
                    )

                scaffold.apply(action, outcome)
                event_data = {
                    "action": action.to_dict(),
                    "outcome": outcome.to_dict() if hasattr(outcome, "to_dict") else outcome,
                    "state": scaffold.state.to_dict(),
                }
                event_type = "action_applied"
                if action.action_type is ActionType.MESSAGE:
                    event_type = "message_routed"
                elif action.metadata.get("review") == "rejected":
                    event_type = "action_rejected"
                trace.record(
                    "scaffold",
                    event_type,
                    actor_id=actor_id,
                    data=event_data,
                )

                if scaffold.done():
                    status = scaffold.state.status
                    break
            else:
                status = "runtime_turn_limit"
        except Exception as exc:
            status = "error"
            error = f"{type(exc).__name__}: {exc}"
            scaffold.state.status = "failed"
            trace.record(
                "runtime",
                "error",
                actor_id=scaffold.state.active_agent_id,
                data={"error": error},
            )

        trace.record(
            "runtime",
            "episode_end",
            data={
                "status": status,
                "output": scaffold.output(),
                "env_steps": env.result()["env_steps"],
                "scaffold_turns": scaffold.state.turn_count,
            },
        )
        env.finish()
        episode = env.result()
        return RunResult(
            status=status,
            output=scaffold.output(),
            env_steps=episode["env_steps"],
            scaffold_turns=scaffold.state.turn_count,
            actions=list(scaffold.state.action_history),
            trace=trace,
            metadata={
                "initial_observation": initial_observation,
                "scaffold": scaffold.state.to_dict(),
                "error": error,
            },
        )
