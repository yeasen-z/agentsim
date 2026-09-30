import json
from pathlib import Path

from agentsim import (
    EpisodeRuntime,
    LLMAdapter,
    MockLLMClient,
    RunResult,
    SingleAgentScaffold,
    as_env,
)
from benchmarks.injecagent import InjecAgentData, evaluate, list_envs, list_tasks
from benchmarks.injecagent.validation import validate_injecagent


def test_dataset_references_registered_tools():
    data = InjecAgentData.load()

    assert len(data.dh_cases) == 510
    assert len(data.ds_cases) == 544
    assert len(data.tools) == 330
    assert len(data.attacker_responses) > 1300
    for case in data.all_cases:
        assert case.user_tool in data.tools
    assert set(case.attacker_tools) <= data.tools.keys()


def test_injecagent_native_conformance_replays_all_user_responses():
    assert validate_injecagent() == []


def test_known_attacker_response_is_returned():
    data = InjecAgentData.load()
    tool_name, arguments_key = next(iter(data.attacker_responses))
    arguments = json.loads(arguments_key)
    env = list_envs()[0]
    task = next(
        task for task in list_tasks(env) if task.source and tool_name in task.source.attacker_tools
    )
    env.reset(task, instruction=task.description)

    result = env.call_tool(tool_name, arguments)

    assert result.success
    assert result.result != {"success": True, "message": f"Tool {tool_name} executed"}


def test_user_tool_reveals_injection_and_attacker_call_is_evaluated():
    env = list_envs()[0]
    task = next(task for task in list_tasks(env) if task.source and task.source.attacker_tools)
    env.reset(task, instruction=task.description)

    user_result = env.call_tool(task.source.user_tool, task.source.tool_parameters)
    attacker_tool = task.source.attacker_tools[0]
    attacker_result = env.call_tool(attacker_tool, {})
    run = RunResult(status="finished", output=None, env_steps=2, scaffold_turns=2)
    result = evaluate(env, task, run)

    assert user_result.success
    assert attacker_result.success
    assert env.env_state.injected is True
    assert env.env_state.attacker_tool_calls[0]["tool_name"] == attacker_tool
    assert result.metrics["attack_success"] is True
    assert result.passed is None
    assert result.metrics["security_success"] is False


def test_mock_agent_runs_complete_episode():
    env = list_envs()[0]
    task = list_tasks(env)[0]
    responses = [
        (
            '{"action_type":"call_tool","tool_name":'
            f'"{task.source.user_tool}","arguments":{json.dumps(task.source.tool_parameters)}'
            "}"
        ),
        '{"action_type":"return","output":"done"}',
    ]
    scaffold = SingleAgentScaffold(LLMAdapter(MockLLMClient(responses)))

    run = EpisodeRuntime(max_scaffold_turns=3).run(as_env(env), scaffold, task)

    assert run.status == "finished"
    assert run.output == "done"
    assert run.env_steps == 1
    assert env.env_state.injected is True


def test_injecagent_data_files_are_installed_resources():
    import benchmarks.injecagent.data as data_module

    data_dir = Path(data_module.__file__).parent / "data"
    assert (data_dir / "tools.json").is_file()
    assert (data_dir / "test_cases_dh_base.json").is_file()
    assert (data_dir / "test_cases_ds_base.json").is_file()
