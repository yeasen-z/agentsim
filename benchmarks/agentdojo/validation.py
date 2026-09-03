"""Deterministic integrity checks for the native AgentDojo adaptation."""

from __future__ import annotations

from dataclasses import replace

from .run import DojoTask, evaluate, list_envs, list_tasks


def replay_user_ground_truths() -> list[str]:
    """Replay every official ground-truth plan and return any failures."""
    failures = []
    for env in list_envs():
        for raw_task in list_tasks(env):
            if not isinstance(raw_task, DojoTask) or raw_task.source is None:
                failures.append(f"{env.suite.name}: invalid task record")
                continue
            env.reset(raw_task, instruction=raw_task.description)
            for call in raw_task.source.ground_truth:
                result = env.call_tool(call.tool, call.arguments)
                if not result.success:
                    failures.append(
                        f"{env.suite.name}:{raw_task.task_id}:{call.tool}: {result.error}"
                    )
                    break
            else:
                evaluation = evaluate(
                    env,
                    raw_task,
                    model_output=raw_task.source.ground_truth_output,
                )
                if evaluation.metrics["utility_success"] is not True:
                    failures.append(
                        f"{env.suite.name}:{raw_task.task_id}: utility evaluation failed"
                    )
    return failures


def replay_injection_ground_truths() -> list[str]:
    """Replay all injection plans and compare their official success outcomes."""
    failures = []
    for env in list_envs():
        base_task = list_tasks(env)[0]
        if not isinstance(base_task, DojoTask):
            failures.append(f"{env.suite.name}: invalid base task record")
            continue
        for injection in env.suite.injection_tasks.values():
            task = replace(base_task, injection=injection, attack_method="direct")
            env.reset(task, instruction=task.description)
            actual_successes = []
            for call in injection.ground_truth:
                result = env.call_tool(call.tool, call.arguments)
                actual_successes.append(result.success)
            expected_successes = [error is None for error in injection.ground_truth_errors]
            if actual_successes != expected_successes:
                failures.append(
                    f"{env.suite.name}:{injection.id}: tool outcomes "
                    f"{actual_successes!r} != {expected_successes!r}"
                )
                continue
            evaluation = evaluate(
                env,
                task,
                model_output=injection.ground_truth_output,
            )
            if evaluation.metrics["attack_success"] is not injection.expected_success:
                failures.append(
                    f"{env.suite.name}:{injection.id}: attack evaluation "
                    f"{evaluation.metrics['attack_success']!r} != {injection.expected_success!r}"
                )
    return failures


def main() -> None:
    failures = [*replay_user_ground_truths(), *replay_injection_ground_truths()]
    if failures:
        raise SystemExit("\n".join(failures))
    print("Replayed all 97 user-task and 35 injection-task ground truths successfully.")


if __name__ == "__main__":
    main()
