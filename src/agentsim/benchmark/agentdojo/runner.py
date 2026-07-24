"""AgentDojo case execution and traversal helpers.

The runner is deliberately agent-agnostic: callers provide an ``AgentAPI``
factory, while this module owns the canonical AgentSim episode loop,
evaluation, state diffs, and optional JSONL persistence.
"""

from __future__ import annotations

import json
from copy import deepcopy
from itertools import islice
from pathlib import Path
from typing import Any, Iterable, Iterator

from agentsim import AgentAPI, as_env

from .attacks import Attack
from .run import Case, evaluate, list_envs, list_tasks


def _snapshot(sim: Any) -> dict[str, Any]:
    return deepcopy(sim.hidden_state.to_dict())


def _diff(before: Any, after: Any, path: str = "$") -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(before.keys() | after.keys()):
            child = f"{path}.{key}"
            if key not in before:
                changes.append({"path": child, "before": "<missing>", "after": after[key]})
            elif key not in after:
                changes.append({"path": child, "before": before[key], "after": "<missing>"})
            else:
                changes.extend(_diff(before[key], after[key], child))
    elif isinstance(before, list) and isinstance(after, list):
        for index in range(max(len(before), len(after))):
            child = f"{path}[{index}]"
            if index >= len(before):
                changes.append({"path": child, "before": "<missing>", "after": after[index]})
            elif index >= len(after):
                changes.append({"path": child, "before": before[index], "after": "<missing>"})
            else:
                changes.extend(_diff(before[index], after[index], child))
    elif before != after:
        changes.append({"path": path, "before": before, "after": after})
    return changes


def iter_cases(
    *,
    suites: Iterable[str] | None = None,
    user_task_ids: Iterable[str] | None = None,
    attack: str | Attack | None = None,
    model_name: str | None = None,
    include_clean: bool = True,
    injection_task_ids: Iterable[str] | None = None,
) -> Iterator[Case]:
    """Yield clean and/or attacked cases using Notebook-style filters.

    A targeted attack expands to ``user task × injection task``. DoS attack
    methods follow AgentDojo and yield one attacked case per user task.
    """

    suite_filter = set(suites) if suites is not None else None
    task_filter = set(user_task_ids) if user_task_ids is not None else None
    injection_filter = set(injection_task_ids) if injection_task_ids is not None else None

    for template in list_envs():
        if suite_filter is not None and template.suite.name not in suite_filter:
            continue
        for task in list_tasks(template):
            if task_filter is not None and task.task_id not in task_filter:
                continue
            if include_clean:
                yield template_case(template, task)
            if attack is None:
                continue
            for case in template_cases(
                template,
                task,
                attack=attack,
                model_name=model_name,
            ):
                if (
                    injection_filter is None
                    or case.task.injection is None
                    or case.task.injection.ID in injection_filter
                ):
                    yield case


def template_case(env: Any, task: Any) -> Case:
    """Build one clean case; kept small for use by custom traversals."""
    from .run import build_cases

    return build_cases(env, task)[0]


def template_cases(
    env: Any,
    task: Any,
    *,
    attack: str | Attack,
    model_name: str | None = None,
) -> list[Case]:
    from .run import build_cases

    return build_cases(env, task, attack=attack, model_name=model_name)


def run_case(
    case: Case,
    agent: AgentAPI,
    *,
    max_steps: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run one case with an AgentSim-compatible agent and evaluate it."""

    if not isinstance(agent, AgentAPI):
        raise TypeError("agent must implement AgentAPI")

    sim = case.env
    env = as_env(sim)
    instruction = case.task.description
    initial_observation = env.reset(case.task, instruction=instruction)
    observation = initial_observation
    tools = [tool.to_dict() for tool in env.tools()]
    history: list[dict[str, Any]] = []
    final_answer = ""
    stop_reason = "max_steps"
    step_limit = max_steps if max_steps is not None else case.task.max_steps
    agent.reset()

    for turn in range(1, step_limit + 1):
        if env.done():
            stop_reason = "environment_done"
            break
        last_result = history[-1]["result"] if history else None
        tool_name, arguments = agent.act(
            instruction=instruction,
            observation=observation,
            available_tools=tools,
            context={"last_tool_result": last_result},
        )
        arguments = arguments or {}
        if tool_name == "finish":
            final_answer = str(arguments.get("answer", ""))
            stop_reason = "final_answer"
            break
        if not tool_name:
            raise RuntimeError("Agent returned no action")

        before = _snapshot(sim)
        result = env.call(tool_name, arguments, agent_id=getattr(agent, "agent_id", "default"))
        after = _snapshot(sim)
        observation = env.observe()
        history.append(
            {
                "turn": turn,
                "tool": tool_name,
                "arguments": arguments,
                "result": result.to_dict(),
                "state_diff": _diff(before, after),
            }
        )

    result = evaluate(sim, case.task, model_output=final_answer)
    return {
        "case": case,
        "sim": sim,
        "evaluation": result,
        "initial_observation": initial_observation,
        "final_answer": final_answer,
        "history": history,
        "stop_reason": stop_reason,
        "secure_utility": result.utility_success and result.secure,
    }


def traverse(
    cases: Iterable[Case],
    agent_factory,
    *,
    output_path: str | Path | None = None,
    max_cases: int | None = None,
    max_steps: int | None = None,
) -> list[dict[str, Any]]:
    """Run cases one by one and optionally persist one detailed JSONL row/case."""

    selected = cases if max_cases is None else islice(cases, max_cases)
    output = Path(output_path) if output_path is not None else None
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.touch(exist_ok=False)

    records: list[dict[str, Any]] = []
    for case in selected:
        try:
            run = run_case(case, agent_factory(), max_steps=max_steps)
            evaluation = run["evaluation"]
            record = {
                "case_id": case.case_id,
                "suite": case.env.suite.name,
                "user_task_id": case.task.task_id,
                "injection_task_id": (
                    case.task.injection.ID if case.task.injection is not None else None
                ),
                "attack_method": case.task.attack_method,
                "attacked": case.attacked,
                "utility_success": evaluation.utility_success,
                "attack_success": evaluation.attack_success,
                "secure": evaluation.secure,
                "secure_utility": run["secure_utility"],
                "steps": len(run["history"]),
                "stop_reason": run["stop_reason"],
                "tool_sequence": [step["tool"] for step in run["history"]],
                "final_answer": run["final_answer"],
                "error": None,
            }
            details = {
                "instruction": case.task.description,
                "initial_observation": run["initial_observation"],
                "final_state": _snapshot(run["sim"]),
                "history": run["history"],
                "trace": (
                    run["sim"].get_trace().to_dict() if run["sim"].get_trace() is not None else None
                ),
                "evaluation": evaluation.to_dict(),
            }
        except Exception as error:
            record = {
                "case_id": case.case_id,
                "suite": case.env.suite.name,
                "user_task_id": case.task.task_id,
                "injection_task_id": (
                    case.task.injection.ID if case.task.injection is not None else None
                ),
                "attack_method": case.task.attack_method,
                "attacked": case.attacked,
                "utility_success": False,
                "attack_success": None,
                "secure": False,
                "secure_utility": False,
                "steps": 0,
                "stop_reason": "error",
                "tool_sequence": [],
                "final_answer": "",
                "error": f"{type(error).__name__}: {error}",
            }
            details = {
                "instruction": case.task.description,
                "initial_observation": None,
                "final_state": None,
                "history": [],
                "trace": None,
                "evaluation": None,
            }

        records.append(record)
        if output is not None:
            with output.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({**record, "details": details}, default=str) + "\n")
    return records
