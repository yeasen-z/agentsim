"""Implement custom runtimes against Agent Sim's canonical interfaces."""

from typing import Any, Dict, List, Optional

from agentsim import (
    Action,
    AgentAPI,
    Env,
    RunResult,
    TaskDefine,
)


def _tools_for_agent(env: Env) -> List[Dict[str, Any]]:
    return [tool.to_dict() for tool in env.tools()]


class SimpleSingleAgentRuntime:
    """Drive one agent until it finishes or exhausts the step budget."""

    def __init__(self, max_steps: int = 10):
        self.max_steps = max_steps

    def run(
        self,
        env: Env,
        agent: AgentAPI,
        task: TaskDefine,
        instruction: str = "",
        config: Optional[Dict[str, Any]] = None,
    ) -> RunResult:
        config = config or {}
        instruction = instruction or task.description or "Complete the task"
        observation = env.reset(task, seed=config.get("seed", 42), instruction=instruction)
        agent.reset()

        action_history: List[Action] = []
        returned_result = ""

        for _ in range(self.max_steps):
            tool_name, arguments = agent.act(
                instruction=instruction,
                observation=observation,
                available_tools=_tools_for_agent(env),
                context={
                    "step": len(action_history) + 1,
                    "history": [action.to_dict() for action in action_history],
                },
            )

            if tool_name in {None, "finish"}:
                returned_result = str((arguments or {}).get("result", ""))
                action_history.append(Action("return_result", result=returned_result))
                break

            if tool_name == "think":
                action_history.append(
                    Action("textual", result=str((arguments or {}).get("message", "")))
                )
                continue

            action = Action("call_tool", tool_name=tool_name, arguments=arguments or {})
            action_history.append(action)
            env.call(tool_name, action.arguments)
            observation = env.observe()

            if env.done():
                break

        episode = env.result()
        status = "finished" if returned_result else "max_steps_reached"
        return RunResult(
            status=status,
            result=returned_result,
            steps_taken=episode["steps_taken"],
            trace_available=env.trace() is not None,
            metadata={
                "actions": [action.to_dict() for action in action_history],
                "episode": episode,
            },
        )


class HumanInLoopRuntime:
    """Ask for approval before each tool call."""

    def __init__(self, max_steps: int = 10, require_approval: bool = True):
        self.max_steps = max_steps
        self.require_approval = require_approval

    def run(
        self,
        env: Env,
        agent: AgentAPI,
        task: TaskDefine,
        instruction: str = "",
        config: Optional[Dict[str, Any]] = None,
    ) -> RunResult:
        config = config or {}
        instruction = instruction or task.description or "Complete the task"
        observation = env.reset(task, seed=config.get("seed", 42), instruction=instruction)
        agent.reset()
        returned_result = ""

        for step in range(1, self.max_steps + 1):
            tool_name, arguments = agent.act(
                instruction=instruction,
                observation=observation,
                available_tools=_tools_for_agent(env),
                context={"step": step},
            )

            if tool_name in {None, "finish"}:
                returned_result = str((arguments or {}).get("result", ""))
                break
            if tool_name == "think":
                continue

            if self.require_approval:
                approval = input(f"Execute {tool_name} with {arguments or {}}? (y/n): ").lower()
                if approval != "y":
                    continue

            env.call(tool_name, arguments or {})
            observation = env.observe()
            if env.done():
                break

        episode = env.result()
        return RunResult(
            status="finished" if returned_result else "max_steps_reached",
            result=returned_result,
            steps_taken=episode["steps_taken"],
            trace_available=env.trace() is not None,
            metadata={"episode": episode},
        )


def demo_custom_runtime() -> None:
    """Print the extension points without starting an interactive episode."""
    print("Custom runtimes implement RuntimeAPI.run().")
    print("They use Env and AgentAPI only.")
    print("The environment records Trace; benchmark evaluation runs afterwards.")


if __name__ == "__main__":
    demo_custom_runtime()
