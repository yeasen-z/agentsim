"""Task traversal and clean/attack variant loading for AgentDyn suites."""

from __future__ import annotations

from typing import Iterable, Iterator, Optional

from benchmarks.common.attacks import Attack

from .env import AgentDynTask, build_tasks, list_envs, list_tasks


def iter_tasks(
    *,
    suites: Optional[Iterable[str]] = None,
    user_task_ids: Optional[Iterable[str]] = None,
    task_ids: Optional[Iterable[str]] = None,
    attack: str | Attack | None = None,
    model_name: Optional[str] = None,
    include_clean: bool = True,
    injection_task_ids: Optional[Iterable[str]] = None,
) -> Iterator[tuple[str, AgentDynTask]]:
    """Yield clean tasks and the official 560 attack cases as suite/task pairs."""
    suite_filter = set(suites) if suites is not None else None
    selected_ids = user_task_ids if user_task_ids is not None else task_ids
    task_filter = set(selected_ids) if selected_ids is not None else None
    injection_filter = set(injection_task_ids) if injection_task_ids is not None else None
    for env in list_envs():
        suite_name = env.suite.name
        if suite_filter is not None and suite_name not in suite_filter:
            continue
        for task in list_tasks(env):
            if task_filter is not None and task.task_id not in task_filter:
                continue
            if include_clean:
                yield suite_name, build_tasks(env, task)[0]
            if attack is None:
                continue
            if task.source is None or not task.source.reachable_vectors:
                continue
            for attacked in build_tasks(env, task, attack=attack, model_name=model_name):
                injection_id = attacked.injection.id if attacked.injection is not None else None
                if injection_filter is None or injection_id in injection_filter:
                    yield suite_name, attacked


TASKS = {env.suite.name: list_tasks(env) for env in list_envs()}
