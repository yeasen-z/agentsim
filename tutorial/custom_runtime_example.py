"""Extend execution mechanics without mixing them into scaffold state."""

from typing import Any, Dict, Optional

from agentsim import Env, EpisodeRuntime, RunResult, ScaffoldAPI, TaskDefine


class InstrumentedRuntime(EpisodeRuntime):
    """Attach deployment metadata while preserving the shared episode loop."""

    def run(
        self,
        env: Env,
        scaffold: ScaffoldAPI,
        task: TaskDefine,
        instruction: str = "",
        config: Optional[Dict[str, Any]] = None,
    ) -> RunResult:
        result = super().run(env, scaffold, task, instruction, config)
        result.metadata["runtime"] = "instrumented"
        return result


def demo_custom_runtime() -> None:
    print("Runtime executes a Scaffold against an Env.")
    print("EnvState, AgentState, and ScaffoldState remain independently owned.")
    print("Trace records events across all boundaries.")


if __name__ == "__main__":
    demo_custom_runtime()
