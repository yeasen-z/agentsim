"""Scaffolds coordinate agents without owning environment state."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional

from ..agent.base import ReviewerAgent
from ..agent.state import AgentMessage, AgentRole
from ..interfaces import Action, ActionType, AgentAPI
from .state import ScaffoldState

PromptBuilder = Callable[
    [str, str, Dict[str, Any], List[Dict[str, Any]], ScaffoldState],
    str,
]


def _serialize(value: Any) -> Any:
    return value.to_dict() if hasattr(value, "to_dict") else value


class BaseScaffold(ABC):
    """Shared mechanics for single- and multi-agent scaffolds."""

    def __init__(
        self,
        agents: Iterable[AgentAPI],
        *,
        scaffold_id: Optional[str] = None,
        max_turns: int = 30,
        agent_prompts: Optional[Mapping[str, str]] = None,
        prompt_builder: Optional[PromptBuilder] = None,
    ):
        agent_list = list(agents)
        if not agent_list:
            raise ValueError("A scaffold requires at least one agent")
        self.agents: Dict[str, AgentAPI] = {agent.agent_id: agent for agent in agent_list}
        if len(self.agents) != len(agent_list):
            raise ValueError("Agent IDs must be unique within a scaffold")
        if max_turns < 1:
            raise ValueError("max_turns must be positive")
        self.scaffold_id = scaffold_id or f"scaffold_{uuid.uuid4().hex[:8]}"
        self.max_turns = max_turns
        self.agent_prompts = dict(agent_prompts or {})
        unknown_prompt_agents = set(self.agent_prompts) - set(self.agents)
        if unknown_prompt_agents:
            raise KeyError(
                f"Prompts configured for unknown agents: {sorted(unknown_prompt_agents)}"
            )
        self.prompt_builder = prompt_builder
        self.state = ScaffoldState(scaffold_id=self.scaffold_id)

    def reset(self) -> None:
        self.state = ScaffoldState(scaffold_id=self.scaffold_id)
        for agent in self.agents.values():
            agent.reset()
        self._reset_scheduler()

    def _reset_scheduler(self) -> None:
        """Reset implementation-specific scheduling cursors."""
        return None

    @abstractmethod
    def select_actor(self) -> Optional[str]:
        """Select the agent that owns the next turn."""

    def act(
        self,
        actor_id: str,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
    ) -> Action:
        if self.done():
            raise RuntimeError("Scaffold is already done")
        if actor_id not in self.agents:
            raise KeyError(f"Unknown scaffold actor: {actor_id}")

        self.state.status = "running"
        self.state.active_agent_id = actor_id
        agent = self.agents[actor_id]
        context = agent.context()
        context["scaffold"] = {
            "scaffold_id": self.scaffold_id,
            "turn": self.state.turn_count + 1,
            "last_outcome": self.state.last_outcomes.get(actor_id),
            "action_history": [action.to_dict() for action in self.state.action_history],
        }
        effective_instruction = self._build_instruction(
            actor_id,
            instruction,
            observation,
            available_tools,
        )
        action = agent.act(effective_instruction, observation, available_tools, context)
        if not isinstance(action, Action):
            raise TypeError("AgentAPI.act() must return Action")
        if action.actor_id != actor_id:
            raise ValueError(f"Selected actor {actor_id!r} returned action for {action.actor_id!r}")
        return self._review(action, context)

    def _build_instruction(
        self,
        actor_id: str,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
    ) -> str:
        """Build the actor-specific prompt owned by this scaffold."""
        if self.prompt_builder is not None:
            return self.prompt_builder(
                actor_id,
                instruction,
                observation,
                available_tools,
                self.state,
            )
        role_prompt = self.agent_prompts.get(actor_id)
        if not role_prompt:
            return instruction
        return f"{role_prompt}\n\nTask:\n{instruction}"

    def _review(self, action: Action, context: Dict[str, Any]) -> Action:
        return action

    def apply(self, action: Action, outcome: Any = None) -> None:
        """Apply an agent action to scaffold-owned state."""
        if action.actor_id not in self.agents:
            raise KeyError(f"Unknown scaffold actor: {action.actor_id}")
        self.state.action_history.append(action)
        self.state.turn_count += 1

        if action.action_type is ActionType.MESSAGE:
            self._route_message(action)
        elif action.action_type is ActionType.CALL_TOOL:
            self.state.env_steps += 1
            self.state.last_outcomes[action.actor_id] = _serialize(outcome)
        elif action.action_type is ActionType.RETURN:
            self.state.final_output = action.output
            self.state.status = "finished"

        if self.state.status != "finished" and self.state.turn_count >= self.max_turns:
            self.state.status = "exhausted"

    def _route_message(self, action: Action) -> None:
        recipient_id = action.recipient_id
        if recipient_id != "*" and recipient_id not in self.agents:
            raise KeyError(f"Unknown message recipient: {recipient_id}")
        message = AgentMessage(
            sender_id=action.actor_id,
            recipient_id=recipient_id or "",
            content=action.content or "",
            metadata=action.metadata,
        )
        self.state.messages.append(message)
        recipients = (
            [agent for agent_id, agent in self.agents.items() if agent_id != action.actor_id]
            if recipient_id == "*"
            else [self.agents[recipient_id]]
        )
        for agent in recipients:
            agent.receive(message)

    def done(self) -> bool:
        return self.state.status in {"finished", "exhausted", "failed"}

    def output(self) -> Any:
        return self.state.final_output

    def agent_states(self) -> Dict[str, Dict[str, Any]]:
        return {agent_id: agent.state.to_dict() for agent_id, agent in self.agents.items()}


class SingleAgentScaffold(BaseScaffold):
    """A scaffold containing exactly one agent."""

    def __init__(
        self,
        agent: AgentAPI,
        *,
        scaffold_id: Optional[str] = None,
        max_turns: int = 30,
        agent_prompts: Optional[Mapping[str, str]] = None,
        prompt_builder: Optional[PromptBuilder] = None,
    ):
        super().__init__(
            [agent],
            scaffold_id=scaffold_id,
            max_turns=max_turns,
            agent_prompts=agent_prompts,
            prompt_builder=prompt_builder,
        )
        self.agent_id = agent.agent_id

    def select_actor(self) -> Optional[str]:
        return None if self.done() else self.agent_id


class MultiAgentScaffold(BaseScaffold):
    """Deterministic multi-agent scaffold with pluggable actor selection."""

    def __init__(
        self,
        agents: Iterable[AgentAPI],
        *,
        mode: str = "round_robin",
        selector: Optional[Callable[[ScaffoldState, Mapping[str, AgentAPI]], Optional[str]]] = None,
        scaffold_id: Optional[str] = None,
        max_turns: int = 60,
        agent_prompts: Optional[Mapping[str, str]] = None,
        prompt_builder: Optional[PromptBuilder] = None,
    ):
        super().__init__(
            agents,
            scaffold_id=scaffold_id,
            max_turns=max_turns,
            agent_prompts=agent_prompts,
            prompt_builder=prompt_builder,
        )
        if mode not in {"round_robin", "hierarchical"}:
            raise ValueError("mode must be 'round_robin' or 'hierarchical'")
        self.mode = mode
        self.selector = selector
        self._cursor = 0

    def _reset_scheduler(self) -> None:
        self._cursor = 0

    def _ordered_agent_ids(self) -> List[str]:
        agent_ids = list(self.agents)
        if self.mode == "hierarchical":
            managers = [
                agent_id
                for agent_id, agent in self.agents.items()
                if agent.role is AgentRole.MANAGER
            ]
            others = [agent_id for agent_id in agent_ids if agent_id not in managers]
            return managers + others
        return agent_ids

    def select_actor(self) -> Optional[str]:
        if self.done():
            return None
        if self.selector is not None:
            actor_id = self.selector(self.state, self.agents)
            if actor_id is not None and actor_id not in self.agents:
                raise KeyError(f"Selector returned unknown actor: {actor_id}")
            return actor_id
        ordered = self._ordered_agent_ids()
        actor_id = ordered[self._cursor % len(ordered)]
        self._cursor += 1
        return actor_id

    def _review(self, action: Action, context: Dict[str, Any]) -> Action:
        if action.action_type is not ActionType.CALL_TOOL:
            return action
        reviewers = [
            agent
            for agent in self.agents.values()
            if (
                isinstance(agent, ReviewerAgent)
                or (
                    getattr(agent, "role", None) is AgentRole.REVIEWER
                    and callable(getattr(agent, "review", None))
                )
            )
            and agent.agent_id != action.actor_id
        ]
        for reviewer in reviewers:
            approved, reason = reviewer.review(action, context)  # type: ignore[attr-defined]
            if not approved:
                return Action(
                    ActionType.THINK,
                    actor_id=action.actor_id,
                    content=f"Action rejected by {reviewer.agent_id}: {reason}",
                    metadata={
                        "reviewer_id": reviewer.agent_id,
                        "review": "rejected",
                        "reason": reason,
                        "proposed_action": action.to_dict(),
                    },
                )
        return action


def create_scaffold(
    agents: Iterable[AgentAPI],
    *,
    mode: str = "round_robin",
    scaffold_id: Optional[str] = None,
    max_turns: Optional[int] = None,
    agent_prompts: Optional[Mapping[str, str]] = None,
    prompt_builder: Optional[PromptBuilder] = None,
) -> BaseScaffold:
    agent_list = list(agents)
    if len(agent_list) == 1:
        return SingleAgentScaffold(
            agent_list[0],
            scaffold_id=scaffold_id,
            max_turns=max_turns or 30,
            agent_prompts=agent_prompts,
            prompt_builder=prompt_builder,
        )
    return MultiAgentScaffold(
        agent_list,
        mode=mode,
        scaffold_id=scaffold_id,
        max_turns=max_turns or 60,
        agent_prompts=agent_prompts,
        prompt_builder=prompt_builder,
    )
