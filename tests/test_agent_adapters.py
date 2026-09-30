from types import SimpleNamespace

import pytest

from agentsim import ActionType, APIStyle, LLMAdapter, OpenAIClient


class RecordingEndpoint:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


def fake_openai_client():
    responses = RecordingEndpoint(
        SimpleNamespace(id="resp_123", output_text='{"action_type":"return","output":"ok"}')
    )
    completions = RecordingEndpoint(
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content='{"action_type":"return","output":"ok"}')
                )
            ]
        )
    )
    return SimpleNamespace(
        responses=responses,
        chat=SimpleNamespace(completions=completions),
    )


def test_openai_responses_client_tracks_response_id():
    sdk = fake_openai_client()
    client = OpenAIClient("test-model", client=sdk)

    output = client.generate(
        input="hello",
        instructions="be concise",
        previous_response_id="resp_old",
        temperature=0.0,
    )

    assert output.endswith('"ok"}')
    assert client.current_response_id == "resp_123"
    assert sdk.responses.calls == [
        {
            "model": "test-model",
            "input": "hello",
            "instructions": "be concise",
            "previous_response_id": "resp_old",
            "temperature": 0.0,
        }
    ]


def test_openai_chat_client_extracts_message_content():
    sdk = fake_openai_client()
    client = OpenAIClient("test-model", api_style=APIStyle.CHAT, client=sdk)
    messages = [{"role": "user", "content": "hello"}]

    output = client.generate(messages=messages)

    assert output.endswith('"ok"}')
    assert sdk.chat.completions.calls == [{"model": "test-model", "messages": messages}]


def test_responses_adapter_forwards_context_and_resets_chain():
    sdk = fake_openai_client()
    client = OpenAIClient("test-model", client=sdk)
    agent = LLMAdapter(client, agent_id="worker")

    action = agent.act(
        "finish",
        {"ready": True},
        [],
        context={
            "messages": [
                {"sender_id": "manager", "content": "please continue"},
                {"sender_id": "worker", "content": "working"},
            ]
        },
    )

    assert action.action_type is ActionType.RETURN
    assert action.output == "ok"
    request_input = sdk.responses.calls[0]["input"]
    assert [item["role"] for item in request_input] == ["user", "assistant", "user"]

    agent.act("finish", {"ready": True}, [])
    assert sdk.responses.calls[1]["previous_response_id"] == "resp_123"

    agent.reset()
    assert client.current_response_id is None


def test_legacy_client_defaults_to_chat_and_can_reset():
    class LegacyClient:
        def generate(self, messages=None, **kwargs):
            assert messages is not None
            return '{"action_type":"return","output":"legacy"}'

    agent = LLMAdapter(LegacyClient())
    action = agent.act("finish", {}, [])
    agent.reset()

    assert action.output == "legacy"


def test_adapter_restores_idle_status_after_client_error():
    class BrokenClient:
        api_style = APIStyle.CHAT

        def generate(self, **kwargs):
            raise RuntimeError("network failure")

    agent = LLMAdapter(BrokenClient())
    with pytest.raises(RuntimeError, match="network failure"):
        agent.act("finish", {}, [])
    assert agent.state.status == "idle"
