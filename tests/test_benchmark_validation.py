from benchmarks.agentdojo.validation import (
    replay_injection_ground_truths as replay_dojo_injection_ground_truths,
)
from benchmarks.agentdojo.validation import (
    replay_user_ground_truths as replay_dojo_user_ground_truths,
)
from benchmarks.agentdyn.data import load_suite
from benchmarks.agentdyn.env import list_envs, list_tasks
from benchmarks.agentdyn.github_tools import _issues_repr
from benchmarks.agentdyn.validation import (
    ReplayContext,
    replay_injection_ground_truths,
    replay_user_ground_truths,
)


def test_agentdojo_ground_truths_replay():
    assert replay_dojo_user_ground_truths() == []
    assert replay_dojo_injection_ground_truths() == []


def test_agentdyn_ground_truths_replay():
    assert replay_user_ground_truths() == []
    assert replay_injection_ground_truths() == []


def test_agentdyn_runtime_placeholders_and_github_fixture_match_upstream():
    github = next(env for env in list_envs() if env.suite.name == "github")
    task = next(task for task in list_tasks(github) if task.task_id == "user_task_9")
    github.reset(task, instruction=task.description)
    context = ReplayContext()
    expected_results = task.source.ground_truth_results
    observed = []
    for index, call in enumerate(task.source.ground_truth):
        expected = expected_results[index]
        result = github.call_tool(call.tool, context.resolve(call, expected, github))
        context.record(expected, result.result)
        observed.append(result.result)

    assert observed[2:5] == list(expected_results[2:5])

    multi_otp = next(task for task in list_tasks(github) if task.task_id == "user_task_12")
    github.reset(multi_otp, instruction=multi_otp.description)
    context = ReplayContext()
    for index, call in enumerate(multi_otp.source.ground_truth):
        expected = multi_otp.source.ground_truth_results[index]
        result = github.call_tool(call.tool, context.resolve(call, expected, github))
        context.record(expected, result.result)
        if call.tool == "verify_github_account":
            assert result.result == expected


def test_agentdyn_invalid_otp_does_not_execute_pending_transaction():
    dailylife = next(env for env in list_envs() if env.suite.name == "dailylife")
    task = next(task for task in list_tasks(dailylife) if task.task_id == "user_task_6")
    dailylife.reset(task, instruction=task.description)
    context = ReplayContext()
    verified_result = None
    for index, call in enumerate(task.source.ground_truth):
        expected = task.source.ground_truth_results[index]
        result = dailylife.call_tool(call.tool, context.resolve(call, expected, dailylife))
        context.record(expected, result.result)
        if call.tool == "verify_transaction":
            verified_result = result.result

    assert verified_result == "One Time Password is incorrect, verification failed."
    account = dailylife.env_state.data["bank_database"]["account_list"][0]
    assert account["verification_stack"]


def test_agentdyn_environment_loading_and_model_serialization_match_upstream():
    github = load_suite("github").environment
    repo_config = github["filesystem"]["root"]["children"]["user"]["children"]["github"][
        "children"
    ]["linear_algebra_operation"]["children"][".git_config"]
    assert repo_config["content"] == '{"repo_name": "emmajohnson/linear_algebra_operation"}'

    # AgentDojo serializes resolved YAML with PyYAML's sorted-key default,
    # then model fields restore their declared Permissions ordering.
    shopping = next(env for env in list_envs() if env.suite.name == "shopping")
    task = next(task for task in list_tasks(shopping) if task.task_id == "user_task_8")
    shopping.reset(task, instruction=task.description)
    listing = shopping.call_tool("list_directory", {"path": "/user/info"}).result
    assert listing.startswith(
        "[{'name': 'alice_info.txt', 'type': 'file', 'permissions': "
        "{'read': True, 'write': True, 'execute': False}}"
    )
    inbox = shopping.env_state.data["email_database"]["inbox_list"][0]
    assert all("attachments" in message for message in inbox["received"])

    assert (
        _issues_repr([{"owner_username": "octocat", "comments": [{"title": "issue"}]}])
        == "[Issues(owner_username='octocat', comments=[{'title': 'issue'}])]"
    )


def test_agentdyn_send_money_confirmation_preserves_upstream_float_format():
    daily = next(env for env in list_envs() if env.suite.name == "dailylife")
    task = next(task for task in list_tasks(daily) if task.task_id == "user_task_7")
    daily.reset(task, instruction=task.description)
    context = ReplayContext()
    result = None
    for index, call in enumerate(task.source.ground_truth):
        expected = task.source.ground_truth_results[index]
        observation = daily.call_tool(call.tool, context.resolve(call, expected, daily))
        context.record(expected, observation.result)
        if call.tool == "send_money":
            result = observation.result
    assert result == "Sent 200.0 to CF8932140215."


def test_agentdyn_shopping_transfer_uses_upstream_banking_sender():
    shopping = next(env for env in list_envs() if env.suite.name == "shopping")
    task = next(task for task in list_tasks(shopping) if task.task_id == "user_task_8")
    shopping.reset(task, instruction=task.description)
    context = ReplayContext()
    for index, call in enumerate(task.source.ground_truth):
        expected = task.source.ground_truth_results[index]
        result = shopping.call_tool(call.tool, context.resolve(call, expected, shopping))
        context.record(expected, result.result)
    inbox = next(
        inbox
        for inbox in shopping.env_state.data["email_database"]["inbox_list"]
        if inbox["account_email"] == "emma.johnson@bluesparrowtech.com"
    )
    transaction_email = next(
        email
        for email in inbox["emails"].values()
        if email["subject"] == "Transaction Approval Request OTP"
    )
    assert transaction_email["sender"] == "banking_platform@mail.com"
