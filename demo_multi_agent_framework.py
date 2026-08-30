"""Runnable four-layer multi-agent example.

The environment owns world state, every agent owns private state, the scaffold
owns communication and scheduling, and Trace records their boundary events.
"""

from __future__ import annotations

from agentsim import (
    Action,
    ActionType,
    AgentRole,
    BaseAgent,
    EnvSim,
    EnvState,
    EpisodeRuntime,
    MultiAgentScaffold,
    ScenarioDefine,
    TaskDefine,
    ToolDefine,
    ToolExecutor,
    as_env,
)


class PlannerAgent(BaseAgent):
    """Delegate work, then return after the worker reports completion."""

    def __init__(self) -> None:
        super().__init__(agent_id="planner", role=AgentRole.MANAGER)

    def act(self, instruction, observation, available_tools, context=None):
        del instruction, observation, available_tools
        messages = (context or {}).get("messages", [])
        if messages:
            return Action(
                ActionType.RETURN,
                actor_id=self.agent_id,
                output=messages[-1]["content"],
            )
        if self.state.context.get("delegated"):
            return Action(ActionType.WAIT, actor_id=self.agent_id)
        self.state.context["delegated"] = True
        return Action(
            ActionType.MESSAGE,
            actor_id=self.agent_id,
            recipient_id="executor",
            content="Calculate 25 * 4 and store the result.",
        )


class ExecutorAgent(BaseAgent):
    """Use environment tools and report the outcome to the planner."""

    def __init__(self) -> None:
        super().__init__(agent_id="executor", role=AgentRole.WORKER)
        self.phase = 0

    def reset(self) -> None:
        super().reset()
        self.phase = 0

    def act(self, instruction, observation, available_tools, context=None):
        del instruction, observation, available_tools
        if self.phase == 0:
            self.phase = 1
            return Action(
                ActionType.CALL_TOOL,
                actor_id=self.agent_id,
                tool_name="calculate",
                arguments={"left": 25, "right": 4},
            )
        if self.phase == 1:
            outcome = (context or {}).get("scaffold", {}).get("last_outcome", {})
            self.phase = 2
            return Action(
                ActionType.CALL_TOOL,
                actor_id=self.agent_id,
                tool_name="store_result",
                arguments={"value": outcome.get("result")},
            )
        return Action(
            ActionType.MESSAGE,
            actor_id=self.agent_id,
            recipient_id="planner",
            content="Stored the result in EnvState.",
        )


def build_environment() -> EnvSim:
    executor = ToolExecutor()
    executor.register_tool(
        "calculate",
        lambda state, left, right: left * right,
        ToolDefine(
            name="calculate",
            description="Multiply two integers.",
            parameters={
                "type": "object",
                "properties": {
                    "left": {"type": "integer"},
                    "right": {"type": "integer"},
                },
                "required": ["left", "right"],
            },
            category="read",
        ),
    )

    def store_result(state: EnvState, value: int) -> dict:
        state.metadata["result"] = value
        return {"stored": value}

    executor.register_tool(
        "store_result",
        store_result,
        ToolDefine(
            name="store_result",
            description="Store the final value in the environment.",
            parameters={
                "type": "object",
                "properties": {"value": {"type": "integer"}},
                "required": ["value"],
            },
            category="write",
        ),
    )
    return EnvSim(
        scenario=ScenarioDefine("calculation", "Calculation"),
        init_state=lambda initial, seed: EnvState(metadata={"seed": seed, **initial}),
        executor=executor,
    )


def main() -> None:
    sim = build_environment()
    task = TaskDefine(
        task_id="calculate-and-store",
        scenario="calculation",
        description="Calculate 25 * 4 and store it.",
        max_steps=3,
    )
    scaffold = MultiAgentScaffold(
        [PlannerAgent(), ExecutorAgent()],
        mode="round_robin",
        max_turns=8,
    )
    run = EpisodeRuntime(max_scaffold_turns=8).run(as_env(sim), scaffold, task)

    assert sim.env_state is not None
    print("output:", run.output)
    print("env result:", sim.env_state.metadata["result"])
    print("trace events:", len(run.trace.events))


if __name__ == "__main__":
    main()
