"""Conformance checks for the native InjecAgent pack."""

from __future__ import annotations

from .env import InjecAgentEnv, list_tasks


def validate_injecagent() -> list[str]:
    """Check inventories, tool references, and injection-response replay."""
    failures: list[str] = []
    env = InjecAgentEnv()
    tool_names = set(env.data.tools)
    tasks = list_tasks(env)

    if len(env.data.dh_cases) != 510 or len(env.data.ds_cases) != 544:
        failures.append(
            f"case inventory was DH={len(env.data.dh_cases)}, DS={len(env.data.ds_cases)}"
        )
    if len(tool_names) != 330:
        failures.append(f"tool inventory was {len(tool_names)}, expected 330")
    if len(env.data.attacker_responses) != 1384:
        failures.append(
            f"attacker response inventory was {len(env.data.attacker_responses)}, expected 1384"
        )

    for task in tasks:
        case = task.source
        if case is None:
            failures.append(f"{task.task_id}: missing source test case")
            continue
        references = {case.user_tool, *case.attacker_tools}
        unknown = references - tool_names
        if unknown:
            failures.append(f"{task.task_id}: unknown tool references {sorted(unknown)}")
            continue

        env.reset(task, instruction=task.description)
        result = env.call_tool(case.user_tool, case.tool_parameters)
        if not result.success:
            failures.append(f"{task.task_id}: user tool failed: {result.error}")
            continue
        if not getattr(env.env_state, "injected", False):
            failures.append(f"{task.task_id}: user tool response was not marked as observed")

    return failures


def main() -> None:
    failures = validate_injecagent()
    if failures:
        raise SystemExit("\n".join(failures))
    print("Validated 1,054 InjecAgent cases, 330 tools, and all user-tool responses.")


if __name__ == "__main__":
    main()
