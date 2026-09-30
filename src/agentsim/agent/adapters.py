"""
TinyAct Emulator - Agent Adapters
Connects LLM models to the agent framework.
"""

import json
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Union

from ..interfaces import Action, ActionType
from .base import SingleAgent
from .state import AgentRole


class APIStyle(str, Enum):
    """LLM API style selection."""

    CHAT = "chat"
    RESPONSES = "responses"


class LLMClient:
    """Abstract LLM client interface.

    Supports two API styles:
    - CHAT: OpenAI Chat Completions API (/v1/chat/completions)
    - RESPONSES: OpenAI Responses API (/v1/responses) with conversation chaining
    """

    def __init__(self, api_style: Union[APIStyle, str] = APIStyle.CHAT):
        self.api_style = APIStyle(api_style) if isinstance(api_style, str) else api_style
        self._response_id: Optional[str] = None

    def generate(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List[Dict[str, Any]]]] = None,
        instructions: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        previous_response_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Generate a response from the LLM.

        Args:
            messages: Chat-style messages (for CHAT API style)
            input: Responses API input - text or list of input items
            instructions: Responses API system instructions
            tools: Available tools for the model
            previous_response_id: Chain to a previous response for context (Responses API only)
            **kwargs: Additional parameters (temperature, model, etc.)

        Returns:
            Generated text response
        """
        raise NotImplementedError

    def reset_conversation(self) -> None:
        """Reset the conversation chain (clears previous_response_id)."""
        self._response_id = None

    @property
    def current_response_id(self) -> Optional[str]:
        """Get the current response ID for conversation chaining."""
        return self._response_id


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""

    def __init__(
        self,
        responses: List[str] = None,
        api_style: Union[APIStyle, str] = APIStyle.CHAT,
    ):
        super().__init__(api_style=api_style)
        self.responses = responses or []
        self.call_count = 0
        self._mock_response_id_counter = 0

    def generate(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List[Dict[str, Any]]]] = None,
        instructions: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        previous_response_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
        else:
            response = '{"action_type": "return", "output": ""}'

        self.call_count += 1
        self._mock_response_id_counter += 1
        self._response_id = f"mock_resp_{self._mock_response_id_counter}"
        return response


class OpenAIClient(LLMClient):
    """OpenAI SDK-backed client for chat completions or Responses API calls.

    The OpenAI dependency is optional. Pass an SDK-compatible client in tests,
    or install ``agentsim[openai]`` for live requests.
    """

    def __init__(
        self,
        model: str,
        *,
        api_style: Union[APIStyle, str] = APIStyle.RESPONSES,
        client: Any = None,
        api_key: Optional[str] = None,
        client_options: Optional[Mapping[str, Any]] = None,
        request_options: Optional[Mapping[str, Any]] = None,
    ):
        super().__init__(api_style=api_style)
        if not model:
            raise ValueError("model must not be empty")
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as error:
                raise ImportError(
                    "OpenAIClient requires the optional dependency; "
                    "install it with `pip install -e '.[openai]'`"
                ) from error
            options = dict(client_options or {})
            if api_key is not None:
                options["api_key"] = api_key
            client = OpenAI(**options)
        self.model = model
        self.client = client
        self.request_options = dict(request_options or {})

    def generate(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List[Dict[str, Any]]]] = None,
        instructions: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        previous_response_id: Optional[str] = None,
        **kwargs,
    ) -> str:
        request = {**self.request_options, **kwargs, "model": self.model}
        if tools:
            request["tools"] = tools

        if self.api_style is APIStyle.RESPONSES:
            if input is None:
                raise ValueError("Responses API calls require input")
            request["input"] = input
            if instructions is not None:
                request["instructions"] = instructions
            if previous_response_id is not None:
                request["previous_response_id"] = previous_response_id
            response = self.client.responses.create(**request)
            self._response_id = response.id
            output_text = response.output_text
            if not isinstance(output_text, str):
                raise TypeError("Responses API output_text must be a string")
            return output_text

        if messages is None:
            raise ValueError("Chat Completions API calls require messages")
        request["messages"] = messages
        response = self.client.chat.completions.create(**request)
        content = response.choices[0].message.content
        if not isinstance(content, str):
            raise TypeError("Chat Completions response content must be a string")
        return content


class LLMAdapter(SingleAgent):
    """
    LLM-based agent adapter.
    Wraps an LLM client to provide tool-calling capabilities.

    Supports two API styles via the LLMClient:
    - CHAT: Traditional chat completions with message history
    - RESPONSES: Responses API with previous_response_id for conversation chaining
    """

    def __init__(
        self,
        llm_client: LLMClient,
        agent_id: str = "llm_agent",
        system_prompt: str = None,
        temperature: float = 0.0,
    ):
        super().__init__(agent_id=agent_id, role=AgentRole.EXECUTOR)
        self.llm_client = llm_client
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.temperature = temperature

    def _default_system_prompt(self) -> str:
        return """You are an AI assistant that helps users complete tasks by using tools.

You will be given:
1. A task instruction
2. Current observation of the environment
3. Available tools with their descriptions and parameters

Your goal is to complete the task by calling appropriate tools with correct arguments.

Respond with a JSON object in this format:
{
    "action_type": "call_tool",
    "tool_name": "tool_name",
    "arguments": {"arg1": "value1", "arg2": "value2"}
}

If the task is complete, return {"action_type": "return", "output": "..."}.
To message another agent, return {"action_type": "message", "recipient_id": "...", "content": "..."}.
To wait, return {"action_type": "wait"}.

Only respond with valid JSON, no other text."""

    def _format_tools_for_llm(self, tools: List[Dict[str, Any]]) -> str:
        """Format tools as natural language description."""
        lines = ["Available tools:"]
        for tool in tools:
            lines.append(f"\n- {tool['name']}: {tool['description']}")
            if tool.get("parameters"):
                params = tool["parameters"]
                if isinstance(params, dict):
                    lines.append(f"  Parameters: {json.dumps(params)}")
        return "\n".join(lines)

    def _parse_llm_response(self, response: str) -> Action:
        """Parse one structured action from an LLM response."""
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)

                action_type = ActionType(data["action_type"])
                return Action(
                    action_type=action_type,
                    actor_id=self.agent_id,
                    tool_name=data.get("tool_name"),
                    arguments=data.get("arguments") or {},
                    output=data.get("output"),
                    recipient_id=data.get("recipient_id"),
                    content=data.get("content"),
                    metadata=data.get("metadata") or {},
                )
        except (KeyError, ValueError, json.JSONDecodeError) as error:
            return Action(
                ActionType.THINK,
                actor_id=self.agent_id,
                content=f"Invalid structured model response: {error}",
                metadata={"raw_response": response},
            )
        return Action(
            ActionType.THINK,
            actor_id=self.agent_id,
            content="Model response contained no JSON object",
            metadata={"raw_response": response},
        )

    def _build_user_message(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
    ) -> str:
        """Build the user message content."""
        tools_desc = self._format_tools_for_llm(available_tools)
        obs_str = json.dumps(observation, indent=2, default=str)

        return f"""Task: {instruction}

Current Observation:
{obs_str}

{tools_desc}

Choose your next action:"""

    def _call_chat_api(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Call using Chat Completions API style."""
        user_message = self._build_user_message(instruction, observation, available_tools)

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]

        if context and context.get("messages"):
            for msg in context["messages"]:
                if msg.get("sender_id") != self.agent_id:
                    messages.append({"role": "user", "content": msg.get("content", "")})
                else:
                    messages.append({"role": "assistant", "content": msg.get("content", "")})

        return self.llm_client.generate(messages=messages, temperature=self.temperature)

    def _call_responses_api(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Call using Responses API style with conversation chaining."""
        user_message = self._build_user_message(instruction, observation, available_tools)

        response_input: Union[str, List[Dict[str, Any]]] = user_message
        if context and context.get("messages"):
            response_input = []
            for message in context["messages"]:
                role = "assistant" if message.get("sender_id") == self.agent_id else "user"
                response_input.append({"role": role, "content": message.get("content", "")})
            response_input.append({"role": "user", "content": user_message})

        previous_response_id = getattr(self.llm_client, "current_response_id", None)

        response = self.llm_client.generate(
            input=response_input,
            instructions=self.system_prompt,
            previous_response_id=previous_response_id,
            temperature=self.temperature,
        )

        return response

    def act(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Action:
        """Generate action using LLM."""
        self.state.status = "thinking"

        try:
            if getattr(self.llm_client, "api_style", APIStyle.CHAT) == APIStyle.RESPONSES:
                response = self._call_responses_api(
                    instruction, observation, available_tools, context
                )
            else:
                response = self._call_chat_api(instruction, observation, available_tools, context)
            return self._parse_llm_response(response)
        finally:
            self.state.status = "idle"

    def reset(self) -> None:
        """Reset agent state and conversation chain."""
        super().reset()
        reset_conversation = getattr(self.llm_client, "reset_conversation", None)
        if callable(reset_conversation):
            reset_conversation()


class HarnessAgent(SingleAgent):
    """
    Agent with harness enhancements.
    The harness provides structured observations and candidate actions.
    """

    def __init__(
        self,
        base_agent: SingleAgent,
        harness_level: int = 0,
        state_compiler: callable = None,
        candidate_generator: callable = None,
    ):
        super().__init__(agent_id=base_agent.agent_id, role=base_agent.role)
        self.base_agent = base_agent
        self.harness_level = harness_level
        self.state_compiler = state_compiler
        self.candidate_generator = candidate_generator

    def act(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Action:
        """Act with harness support."""

        # H1: Structured observation
        if self.harness_level >= 1 and self.state_compiler:
            observation = self.state_compiler(observation, instruction)

        # H2: Candidate actions
        if self.harness_level >= 2 and self.candidate_generator:
            candidates = self.candidate_generator(
                instruction=instruction, observation=observation, available_tools=available_tools
            )

            # Add candidates to context
            if context is None:
                context = {}
            context["candidate_actions"] = candidates

            # Simplified decision: just pick from candidates
            if isinstance(candidates, list) and len(candidates) == 1:
                return Action(
                    ActionType.CALL_TOOL,
                    actor_id=self.agent_id,
                    tool_name=candidates[0]["tool_name"],
                    arguments=candidates[0]["arguments"],
                )

        # Delegate to base agent
        return self.base_agent.act(
            instruction=instruction,
            observation=observation,
            available_tools=available_tools,
            context=context,
        )
