"""
TinyAct Emulator - Agent Adapters
Connects LLM models to the agent framework.
"""
from typing import Any, Dict, List, Optional, Tuple
import json

from agent_sim.multi_agent import SingleAgent, AgentRole


class LLMClient:
    """Abstract LLM client interface."""
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Generate a response from the LLM."""
        raise NotImplementedError


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""
    
    def __init__(self, responses: List[str] = None):
        self.responses = responses or []
        self.call_count = 0
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
        else:
            response = '{"tool": "finish", "args": {}}'
        
        self.call_count += 1
        return response


class LLMAdapter(SingleAgent):
    """
    LLM-based agent adapter.
    Wraps an LLM client to provide tool-calling capabilities.
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        agent_id: str = "llm_agent",
        system_prompt: str = None,
        temperature: float = 0.0
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
    "tool": "tool_name",
    "args": {"arg1": "value1", "arg2": "value2"}
}

If the task is complete, use tool "finish" with empty args.
If you need to think or ask for clarification, use tool "think" with a "message" argument.

Only respond with valid JSON, no other text."""
    
    def _format_tools_for_llm(self, tools: List[Dict[str, Any]]) -> str:
        """Format tools as natural language description."""
        lines = ["Available tools:"]
        for tool in tools:
            lines.append(f"\n- {tool['name']}: {tool['description']}")
            if tool.get('parameters'):
                params = tool['parameters']
                if isinstance(params, dict):
                    lines.append(f"  Parameters: {json.dumps(params)}")
        return "\n".join(lines)
    
    def _parse_llm_response(self, response: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Parse LLM response into tool call."""
        try:
            # Try to extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                
                tool_name = data.get('tool') or data.get('action')
                args = data.get('args') or data.get('arguments') or {}
                
                return tool_name, args
            else:
                return None, None
        except (json.JSONDecodeError, Exception):
            return None, None
    
    def act(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Dict[str, Any] = None
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Generate action using LLM."""
        self.state.status = "thinking"
        
        # Build prompt
        tools_desc = self._format_tools_for_llm(available_tools)
        
        obs_str = json.dumps(observation, indent=2, default=str)
        
        user_message = f"""Task: {instruction}

Current Observation:
{obs_str}

{tools_desc}

Choose your next action:"""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Add context messages if available
        if context and context.get("messages"):
            for msg in context["messages"]:
                if msg.get("sender_id") != self.agent_id:
                    messages.append({"role": "user", "content": msg.get("content", "")})
                else:
                    messages.append({"role": "assistant", "content": msg.get("content", "")})
        
        # Call LLM
        response = self.llm_client.generate(
            messages=messages,
            temperature=self.temperature
        )
        
        # Parse response
        tool_name, args = self._parse_llm_response(response)
        
        self.state.status = "idle"
        return tool_name, args


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
        candidate_generator: callable = None
    ):
        super().__init__(
            agent_id=base_agent.agent_id,
            role=base_agent.role
        )
        self.base_agent = base_agent
        self.harness_level = harness_level
        self.state_compiler = state_compiler
        self.candidate_generator = candidate_generator
    
    def act(
        self,
        instruction: str,
        observation: Dict[str, Any],
        available_tools: List[Dict[str, Any]],
        context: Dict[str, Any] = None
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Act with harness support."""
        
        # H1: Structured observation
        if self.harness_level >= 1 and self.state_compiler:
            observation = self.state_compiler(observation, instruction)
        
        # H2: Candidate actions
        if self.harness_level >= 2 and self.candidate_generator:
            candidates = self.candidate_generator(
                instruction=instruction,
                observation=observation,
                available_tools=available_tools
            )
            
            # Add candidates to context
            if context is None:
                context = {}
            context["candidate_actions"] = candidates
            
            # Simplified decision: just pick from candidates
            if isinstance(candidates, list) and len(candidates) == 1:
                return candidates[0]["tool_name"], candidates[0]["arguments"]
        
        # Delegate to base agent
        return self.base_agent.act(
            instruction=instruction,
            observation=observation,
            available_tools=available_tools,
            context=context
        )
