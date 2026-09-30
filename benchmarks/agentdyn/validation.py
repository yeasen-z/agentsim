"""Deterministic correctness gates for AgentDyn's native pack."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from .env import AgentDynEnv, AgentDynState, evaluate, list_envs, list_tasks


class ReplayContext:
    """Resolve run-specific values in the frozen upstream golden trace."""

    def __init__(self) -> None:
        self.call_results: list[Any] = []
        self.bindings: dict[str, Any] = {}

    @staticmethod
    def _otps(value: Any) -> list[str]:
        if isinstance(value, str):
            return re.findall(r"OTP\D{0,30}(\d{6})", value, flags=re.IGNORECASE)
        if isinstance(value, dict):
            return [token for item in value.values() for token in ReplayContext._otps(item)]
        if isinstance(value, (list, tuple)):
            return [token for item in value for token in ReplayContext._otps(item)]
        return []

    def resolve(self, call, expected_result: Any, env: AgentDynEnv) -> dict[str, Any]:
        arguments = dict(call.arguments)
        placeholders = call.placeholder_arguments or {}
        for key, marker in placeholders.items():
            if marker != "$6-digits":
                continue
            original = arguments.get(key)
            if original in self.bindings:
                arguments[key] = self.bindings[original]
                continue
            if (
                isinstance(expected_result, str)
                and "One Time Password is incorrect" in expected_result
            ):
                continue
            pending = self._pending_tokens(env, call.tool)
            if len(pending) == 1:
                arguments[key] = pending[0]
        return arguments

    @staticmethod
    def _pending_tokens(env: AgentDynEnv, tool_name: str) -> list[str]:
        if not isinstance(env.env_state, AgentDynState):
            return []
        if tool_name == "verify_github_account":
            platform = env.env_state.data["github_platform"]
            account_key, account_value = "email", platform.get("current_account_email")
        else:
            platform = env.env_state.data["shopping_platform"]
            account_key, account_value = "username", platform.get("current_account_username")
        account = next(
            (item for item in platform["account_list"] if item.get(account_key) == account_value),
            None,
        )
        return list(account.get("verification_stack", {})) if account is not None else []

    def record(self, expected_result: Any, actual_result: Any) -> None:
        self.call_results.append(actual_result)
        expected_otps = self._otps(expected_result)
        actual_otps = self._otps(actual_result)
        for expected, actual in zip(expected_otps, actual_otps, strict=False):
            self.bindings[expected] = actual


def replay_user_ground_truths() -> list[str]:
    """Check all 60 plans, including the explicit validity split."""
    failures: list[str] = []
    replayed = 0
    valid_tasks = 0
    valid_calls = 0
    invalid_tasks = 0
    invalid_calls = 0

    for env in list_envs():
        for task in list_tasks(env):
            source = task.source
            if source is None:
                failures.append(f"{env.suite.name}:{task.task_id}: missing source")
                continue
            replayed += 1
            env.reset(task, instruction=task.description)
            context = ReplayContext()
            results = []
            for index, call in enumerate(source.ground_truth):
                expected_result = (
                    source.ground_truth_results[index]
                    if index < len(source.ground_truth_results)
                    else None
                )
                arguments = context.resolve(call, expected_result, env)
                result = env.call_tool(call.tool, arguments)
                results.append(result)
                context.record(expected_result, result.result)
                expected_error = (
                    source.ground_truth_errors[index]
                    if index < len(source.ground_truth_errors)
                    else None
                )
                if expected_error is not None and result.success:
                    failures.append(
                        f"{env.suite.name}:{task.task_id}:{call.tool}: expected "
                        f"error {expected_error!r}, got success"
                    )
                elif expected_error is None and not result.success:
                    failures.append(
                        f"{env.suite.name}:{task.task_id}:{call.tool}: unexpected error "
                        f"{result.error}"
                    )

            if not isinstance(env.env_state, AgentDynState) or env.pre_environment is None:
                failures.append(f"{env.suite.name}:{task.task_id}: missing native state")
                continue

            if source.ground_truth_valid:
                valid_tasks += 1
                valid_calls += len(source.ground_truth)
                evaluation = evaluate(env, task, source.ground_truth_output)
                if evaluation.metrics["utility_success"] is not True:
                    failures.append(
                        f"{env.suite.name}:{task.task_id}: valid utility ground truth failed"
                    )
            else:
                invalid_tasks += 1
                invalid_calls += len(source.ground_truth)
                evaluation = evaluate(env, task, source.ground_truth_output)
                if evaluation.metrics["utility_success"] is not None:
                    failures.append(
                        f"{env.suite.name}:{task.task_id}: invalid utility ground truth "
                        "must remain unscored"
                    )

    if replayed != 60:
        failures.append(f"replayed {replayed} user tasks, expected 60")
    if valid_tasks != 45 or valid_calls != 322:
        failures.append(
            f"valid inventory was {valid_tasks} tasks/{valid_calls} calls, expected 45/322"
        )
    if invalid_tasks != 15 or invalid_calls != 112:
        failures.append(
            f"invalid inventory was {invalid_tasks} tasks/{invalid_calls} calls, expected 15/112"
        )
    return failures


def replay_injection_ground_truths() -> list[str]:
    """Run each injection task's declared harmful action and check its oracle."""
    failures: list[str] = []
    replayed = 0

    for env in list_envs():
        base_task = list_tasks(env)[0]
        if base_task.source is None:
            failures.append(f"{env.suite.name}: missing base task source")
            continue
        for injection in env.suite.injection_tasks.values():
            replayed += 1
            task = replace(
                base_task,
                injection=injection,
                injections=dict.fromkeys(
                    base_task.source.reachable_vectors, f"TEST: {injection.goal}"
                ),
                attack_method="direct",
            )
            env.reset(task, instruction=task.description)
            context = ReplayContext()
            for index, call in enumerate(injection.ground_truth):
                expected_result = (
                    injection.ground_truth_results[index]
                    if index < len(injection.ground_truth_results)
                    else None
                )
                arguments = context.resolve(call, expected_result, env)
                result = env.call_tool(call.tool, arguments)
                context.record(expected_result, result.result)
                expected_error = (
                    injection.ground_truth_errors[index]
                    if index < len(injection.ground_truth_errors)
                    else None
                )
                if expected_error is not None and result.success:
                    failures.append(
                        f"{env.suite.name}:{injection.id}:{call.tool}: expected "
                        f"error {expected_error!r}, got success"
                    )
                elif expected_error is None and not result.success:
                    failures.append(
                        f"{env.suite.name}:{injection.id}:{call.tool}: unexpected error "
                        f"{result.error}"
                    )

            evaluation = evaluate(env, task, injection.ground_truth_output)
            actual = evaluation.metrics["attack_success"]
            if actual is not injection.expected_success:
                failures.append(
                    f"{env.suite.name}:{injection.id}: attack outcome "
                    f"{actual!r} != expected {injection.expected_success!r}"
                )

    if replayed != 28:
        failures.append(f"replayed {replayed} injection tasks, expected 28")
    return failures


def main() -> None:
    failures = [*replay_user_ground_truths(), *replay_injection_ground_truths()]
    if failures:
        raise SystemExit("\n".join(failures))
    print(
        "Passed 45 valid user tasks/322 calls, inventoried 15 invalid tasks/112 calls, "
        "and replayed 28 injection outcomes."
    )


if __name__ == "__main__":
    main()
