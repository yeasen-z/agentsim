"""
Demo: Connecting SingleAgentRuntime with Agent-Sim Environment

This demo shows how to bridge your SingleAgentRuntime with the agent-sim 
environment (OperationEmulator, ToolExecutor, etc.).

The key is creating adapters that translate between:
- agentcoup.agents.LLMAgent <-> agent_sim.multi_agent.BaseAgent
- agentcoup.tools.ToolRegistry <-> agent_sim.core.ToolExecutor
- agent_sim.core.OperationEmulator -> provides environment state
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import sys

sys.path.insert(0, '/workspace/agent-sim')

# Import from agent-sim
from agent_sim.core import (
    HiddenState, TaskDefinition, ScenarioDefinition,
    ToolExecutor, ToolDefinition, ToolRiskLevel, ToolCall, ToolResult,
    Verifier, VerificationResult,
    Trace, StepRecord, ToolCallRecord
)
from agent_sim.emulator import OperationEmulator
from agent_sim.multi_agent import SingleAgent, AgentRole, BaseAgent
from agent_sim.agents.adapters import LLMClient, LLMAdapter, MockLLMClient


# ============================================================================
# Part 1: Define agentcoup-like interfaces (simulated)
# ============================================================================

@dataclass
class AgentInput:
    """Input to an agent."""
    instruction: str
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "instruction": self.instruction,
            "context": self.context
        }


@dataclass
class AgentState:
    """State maintained by an agent during execution."""
    instruction: str = ""
    observation: Dict[str, Any] = field(default_factory=dict)
    tool_history: List[Dict[str, Any]] = field(default_factory=list)
    runtime_events: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "instruction": self.instruction,
            "observation": self.observation,
            "tool_history": self.tool_history,
            "runtime_events": self.runtime_events
        }


@dataclass
class AgentAction:
    """Action decided by an agent."""
    action_type: str  # "call_tool", "return_result", "textual_tool_call"
    tool: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    tool_call_id: str = ""
    
    @classmethod
    def call_tool(cls, tool: str, arguments: Dict[str, Any], tool_call_id: str = "") -> "AgentAction":
        return cls(
            action_type="call_tool",
            tool=tool,
            arguments=arguments,
            tool_call_id=tool_call_id or f"call_{id(arguments)}"
        )
    
    @classmethod
    def return_result(cls, result: str) -> "AgentAction":
        return cls(
            action_type="return_result",
            result=result
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "tool": self.tool,
            "arguments": self.arguments,
            "result": self.result,
            "tool_call_id": self.tool_call_id
        }


@dataclass
class ToolInteraction:
    """Result of a tool interaction."""
    tool_call_id: str
    tool: str
    arguments: Dict[str, Any]
    result: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_call_id": self.tool_call_id,
            "tool": self.tool,
            "arguments": self.arguments,
            "result": self.result
        }


class ToolSpec:
    """Specification of a tool."""
    def __init__(self, name: str, description: str, parameters: Dict[str, Any]):
        self.name = name
        self.description = description
        self.parameters = parameters
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class ToolRegistry:
    """Registry of tools that can be invoked."""
    
    def __init__(self):
        self._tools: Dict[str, callable] = {}
        self._specs: Dict[str, ToolSpec] = {}
    
    def register(self, name: str, func: callable, spec: ToolSpec):
        self._tools[name] = func
        self._specs[name] = spec
    
    def specs_for(self, allowlist: List[str]) -> List[Dict[str, Any]]:
        """Get tool specs for allowed tools."""
        if not allowlist:
            return [spec.to_dict() for spec in self._specs.values()]
        return [self._specs[name].to_dict() for name in allowlist if name in self._specs]
    
    def invoke(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Invoke a tool with arguments."""
        if tool_name not in self._tools:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                arguments=arguments,
                error=f"Unknown tool: {tool_name}"
            )
        
        try:
            result = self._tools[tool_name](**arguments)
            return ToolResult(
                success=True,
                tool_name=tool_name,
                arguments=arguments,
                result=result
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                arguments=arguments,
                error=str(e)
            )


class AgentSpec:
    """Specification of an agent."""
    def __init__(self, agent_id: str, tool_allowlist: List[str] = None):
        self.agent_id = agent_id
        self.tool_allowlist = tool_allowlist or []


class LLMAgent:
    """LLM-based agent interface."""
    
    def __init__(self, spec: AgentSpec):
        self.spec = spec
    
    def prepare(self, agent_input: AgentInput) -> AgentState:
        """Prepare initial state from input."""
        return AgentState(
            instruction=agent_input.instruction,
            observation=agent_input.context.get("observation", {})
        )
    
    def decide(
        self, 
        state: AgentState, 
        available_tools: List[Dict[str, Any]]
    ) -> AgentAction:
        """Decide on next action given state and available tools."""
        raise NotImplementedError


# ============================================================================
# Part 2: Adapter - Connects agent-sim components to agentcoup interfaces
# ============================================================================

class AgentSimAgentAdapter(LLMAgent):
    """
    Adapts an agent-sim BaseAgent (e.g., LLMAdapter) to the LLMAgent interface.
    
    This adapter:
    - Wraps an agent-sim agent (like LLMAdapter)
    - Translates prepare() to reset the environment
    - Translates decide() to call agent.act() and parse the response
    """
    
    def __init__(
        self, 
        base_agent: BaseAgent, 
        agent_id: str = "adapted_agent",
        tool_allowlist: List[str] = None
    ):
        spec = AgentSpec(agent_id=agent_id, tool_allowlist=tool_allowlist or [])
        super().__init__(spec)
        self.base_agent = base_agent
        self._current_observation: Dict[str, Any] = {}
        self._current_instruction: str = ""
    
    def prepare(self, agent_input: AgentInput) -> AgentState:
        """Prepare state from input."""
        self._current_instruction = agent_input.instruction
        self._current_observation = agent_input.context.get("observation", {})
        
        return AgentState(
            instruction=self._current_instruction,
            observation=self._current_observation
        )
    
    def decide(
        self, 
        state: AgentState, 
        available_tools: List[Dict[str, Any]]
    ) -> AgentAction:
        """
        Use the base agent to decide on an action.
        
        The base agent returns (tool_name, args), which we translate to AgentAction.
        """
        # Call the base agent's act method
        tool_name, args = self.base_agent.act(
            instruction=self._current_instruction,
            observation=state.observation,
            available_tools=available_tools,
            context={"tool_history": state.tool_history}
        )
        
        # Handle special cases
        if tool_name is None:
            # No action - return empty result
            return AgentAction.return_result("No action decided")
        
        if tool_name == "finish":
            # Agent wants to finish
            return AgentAction.return_result(args.get("message", "Task completed"))
        
        if tool_name == "think":
            # Agent wants to think - treat as textual tool call
            return AgentAction(
                action_type="textual_tool_call",
                result=args.get("message", "Thinking...")
            )
        
        # Normal tool call
        return AgentAction.call_tool(
            tool=tool_name,
            arguments=args or {},
            tool_call_id=f"call_{len(state.tool_history) + 1}"
        )


class AgentSimToolRegistryAdapter(ToolRegistry):
    """
    Adapts agent-sim's ToolExecutor + OperationEmulator to ToolRegistry interface.
    
    This adapter:
    - Wraps a ToolExecutor and OperationEmulator
    - Provides specs_for() to list available tools
    - Provides invoke() that executes through the emulator
    """
    
    def __init__(
        self, 
        emulator: OperationEmulator,
        tool_executor: ToolExecutor,
        forbidden_tools: List[str] = None
    ):
        super().__init__()
        self.emulator = emulator
        self.tool_executor = tool_executor
        self.forbidden_tools = set(forbidden_tools or [])
        
        # Load tools from tool_executor
        self._load_tools()
    
    def _load_tools(self):
        """Load tools from the tool executor."""
        for tool_def in self.tool_executor.get_available_tools():
            if tool_def.name in self.forbidden_tools:
                continue
            
            # Create a wrapper function that calls through the emulator
            def make_wrapper(tool_name: str):
                def wrapper(**kwargs):
                    result = self.emulator.call_tool(tool_name, kwargs)
                    if result.success:
                        return result.result
                    else:
                        raise RuntimeError(result.error or result.message)
                return wrapper
            
            self.register(
                name=tool_def.name,
                func=make_wrapper(tool_def.name),
                spec=ToolSpec(
                    name=tool_def.name,
                    description=tool_def.description,
                    parameters=tool_def.parameters
                )
            )
    
    def specs_for(self, allowlist: List[str]) -> List[Dict[str, Any]]:
        """Get specs for allowed tools."""
        if not allowlist:
            # Return all non-forbidden tools
            return [
                spec.to_dict() 
                for name, spec in self._specs.items() 
                if name not in self.forbidden_tools
            ]
        
        # Return only allowed tools
        return [
            self._specs[name].to_dict() 
            for name in allowlist 
            if name in self._specs and name not in self.forbidden_tools
        ]


# ============================================================================
# Part 3: Your SingleAgentRuntime (unchanged from your original)
# ============================================================================

@dataclass
class SingleAgentRuntime:
    agent: LLMAgent
    tools: ToolRegistry
    max_steps: int = 8
    trace: list[dict[str, Any]] = field(default_factory=list)

    def run(self, agent_input: AgentInput) -> dict[str, Any]:
        self.trace = []
        state = self.agent.prepare(agent_input)
        executed_tool_calls: set[tuple[str, str]] = set()
        for step_id in range(1, self.max_steps + 1):
            action = self.agent.decide(
                state,
                available_tools=self.tools.specs_for(self.agent.spec.tool_allowlist),
            )
            self.trace.append(
                {
                    "edge_type": "agent_action",
                    "step_id": step_id,
                    "agent": self.agent.spec.agent_id,
                    "action": action.to_dict(),
                }
            )

            if action.action_type == "call_tool":
                call_key = _tool_call_key(action)
                if call_key in executed_tool_calls:
                    state.runtime_events.append(self._block_duplicate_tool_call(step_id, action))
                    continue
                executed_tool_calls.add(call_key)
                interaction = self._execute_tool(step_id, action)
                if interaction is not None:
                    state.tool_history.append(interaction.to_dict())
                continue

            if action.action_type == "return_result":
                return {
                    "status": "finished",
                    "result": action.result,
                    "steps": step_id,
                    "trace": self.trace,
                }

            if action.action_type == "textual_tool_call":
                return {
                    "status": "textual_tool_call_unexecuted",
                    "raw_content": action.result,
                    "steps": step_id,
                    "trace": self.trace,
                }

        return {
            "status": "max_steps_reached",
            "result": None,
            "steps": self.max_steps,
            "trace": self.trace,
        }

    def _block_duplicate_tool_call(
        self,
        step_id: int,
        action: AgentAction,
    ) -> dict[str, Any]:
        event = {
            "event_type": "duplicate_tool_call_blocked",
            "tool": action.tool,
            "arguments": action.arguments,
            "message": (
                "This tool call has already been executed with the same arguments "
                "during this task. Use the existing observation to answer normally."
            ),
        }
        self.trace.append(
            {
                "edge_type": "duplicate_tool_call_blocked",
                "step_id": step_id,
                "caller": self.agent.spec.agent_id,
                "tool": action.tool,
                "arguments": action.arguments,
            }
        )
        return event

    def _execute_tool(self, step_id: int, action: AgentAction) -> ToolInteraction | None:
        if action.tool is None:
            self.trace.append(
                {
                    "edge_type": "tool_call",
                    "step_id": step_id,
                    "caller": self.agent.spec.agent_id,
                    "tool": None,
                    "tool_call_id": action.tool_call_id,
                    "ok": False,
                    "error": "call_tool action missing tool name",
                }
            )
            return None

        if action.tool not in self.agent.spec.tool_allowlist and self.agent.spec.tool_allowlist:
            self.trace.append(
                {
                    "edge_type": "tool_call",
                    "step_id": step_id,
                    "caller": self.agent.spec.agent_id,
                    "tool": action.tool,
                    "tool_call_id": action.tool_call_id,
                    "ok": False,
                    "error": f"Tool not allowed for agent: {action.tool}",
                }
            )
            return None

        result = self.tools.invoke(action.tool, action.arguments)
        result_dict = result.to_dict()
        self.trace.append(
            {
                "edge_type": "tool_call",
                "step_id": step_id,
                "caller": self.agent.spec.agent_id,
                "tool": action.tool,
                "tool_call_id": action.tool_call_id,
                "arguments": action.arguments,
                "result": result_dict,
            }
        )
        return ToolInteraction(
            tool_call_id=action.tool_call_id,
            tool=action.tool,
            arguments=action.arguments,
            result=result_dict,
        )


def _tool_call_key(action: AgentAction) -> tuple[str, str]:
    return (
        action.tool or "",
        repr(sorted(action.arguments.items())),
    )


# ============================================================================
# Part 4: Demo - Create a scenario and run it through SingleAgentRuntime
# ============================================================================

def create_demo_scenario():
    """Create a simple demo scenario with tools."""
    
    # Define tool functions
    def read_file_func(path: str) -> Dict[str, Any]:
        return {"content": f"Content of {path}", "size": 100}
    
    def write_file_func(path: str, content: str) -> Dict[str, Any]:
        return {"success": True, "path": path, "bytes_written": len(content)}
    
    def list_files_func(folder: str) -> List[str]:
        return [f"{folder}/file1.txt", f"{folder}/file2.txt"]
    
    # Create tool executor and register tools
    tool_executor = ToolExecutor()
    
    tool_executor.register_tool(
        "read_file",
        lambda state, **kwargs: read_file_func(**kwargs),
        ToolDefinition(
            name="read_file",
            description="Read content of a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"]
            },
            risk_level=ToolRiskLevel.SAFE,
            category="read"
        )
    )
    
    tool_executor.register_tool(
        "write_file",
        lambda state, **kwargs: write_file_func(**kwargs),
        ToolDefinition(
            name="write_file",
            description="Write content to a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["path", "content"]
            },
            risk_level=ToolRiskLevel.MODERATE,
            category="write"
        )
    )
    
    tool_executor.register_tool(
        "list_files",
        lambda state, **kwargs: list_files_func(**kwargs),
        ToolDefinition(
            name="list_files",
            description="List files in a folder",
            parameters={
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Folder path"}
                },
                "required": ["folder"]
            },
            risk_level=ToolRiskLevel.SAFE,
            category="read"
        )
    )
    
    # Create a simple state initializer
    def init_state(config: dict, seed: int) -> HiddenState:
        state = HiddenState()
        state.metadata = {"seed": seed, "folder": "/home/user"}
        state.entities = {"files": []}
        return state
    
    # Create a simple verifier
    verifier = Verifier()
    
    # Create scenario definition
    scenario = ScenarioDefinition(
        scenario_id="file_ops_demo",
        name="File Operations Demo",
        description="Demo scenario for file operations",
        state_schema=["files"],
        tools={
            "read": ["read_file", "list_files"],
            "write": ["write_file"]
        },
        tasks=["demo_task"]
    )
    
    # Create emulator
    emulator = OperationEmulator(
        scenario=scenario,
        state_initializer=init_state,
        tool_executor=tool_executor,
        verifier=verifier
    )
    
    return emulator, tool_executor


def run_demo():
    """Run the complete demo showing how SingleAgentRuntime connects to agent-sim."""
    
    print("=" * 70)
    print("DEMO: Connecting SingleAgentRuntime with Agent-Sim")
    print("=" * 70)
    
    # Step 1: Create agent-sim environment
    print("\n1. Creating agent-sim environment...")
    emulator, tool_executor = create_demo_scenario()
    print(f"   ✓ Created emulator with scenario: {emulator.scenario.scenario_id}")
    print(f"   ✓ Registered tools: {[t.name for t in tool_executor.get_available_tools()]}")
    
    # Step 2: Create tool registry adapter
    print("\n2. Creating ToolRegistry adapter...")
    tool_registry = AgentSimToolRegistryAdapter(
        emulator=emulator,
        tool_executor=tool_executor,
        forbidden_tools=[]
    )
    print(f"   ✓ Adapted {len(tool_registry._tools)} tools to ToolRegistry interface")
    
    # Step 3: Create agent with mock LLM
    print("\n3. Creating agent with mock LLM client...")
    
    # Mock responses that simulate an agent listing files, reading one, then finishing
    mock_responses = [
        '{"tool": "list_files", "args": {"folder": "/home/user"}}',
        '{"tool": "read_file", "args": {"path": "/home/user/file1.txt"}}',
        '{"tool": "finish", "args": {"message": "I have read the file content"}}'
    ]
    
    mock_llm = MockLLMClient(responses=mock_responses)
    base_agent = LLMAdapter(llm_client=mock_llm, agent_id="demo_agent")
    
    # Wrap in agentcoup-compatible adapter
    agent = AgentSimAgentAdapter(
        base_agent=base_agent,
        agent_id="demo_agent",
        tool_allowlist=["list_files", "read_file", "write_file"]
    )
    print(f"   ✓ Created AgentSimAgentAdapter for agent: {agent.spec.agent_id}")
    
    # Step 4: Create SingleAgentRuntime
    print("\n4. Creating SingleAgentRuntime...")
    runtime = SingleAgentRuntime(
        agent=agent,
        tools=tool_registry,
        max_steps=5
    )
    print(f"   ✓ Runtime configured with max_steps={runtime.max_steps}")
    
    # Step 5: Prepare agent input with initial observation from emulator
    print("\n5. Preparing agent input...")
    task = TaskDefinition(
        task_id="demo_task",
        scenario="file_ops_demo",
        max_steps=5
    )
    
    initial_obs = emulator.reset(task, seed=42, instruction="List and read files")
    agent_input = AgentInput(
        instruction="List files in /home/user and read the first file",
        context={"observation": initial_obs}
    )
    print(f"   ✓ Initial observation: {initial_obs}")
    
    # Step 6: Run the runtime!
    print("\n6. Running SingleAgentRuntime...")
    print("-" * 70)
    
    result = runtime.run(agent_input)
    
    print("-" * 70)
    print(f"\n7. Execution Result:")
    print(f"   Status: {result['status']}")
    print(f"   Steps: {result['steps']}")
    print(f"   Result: {result.get('result', 'N/A')}")
    
    # Print trace summary
    print(f"\n8. Trace Summary ({len(result['trace'])} events):")
    for event in result['trace']:
        edge_type = event.get('edge_type', 'unknown')
        step_id = event.get('step_id', '?')
        
        if edge_type == 'agent_action':
            action = event.get('action', {})
            print(f"   Step {step_id}: Agent decided to {action.get('action_type', '?')}")
            if action.get('tool'):
                print(f"           Tool: {action['tool']}({action.get('arguments', {})})")
        
        elif edge_type == 'tool_call':
            tool = event.get('tool', 'unknown')
            ok = event.get('ok', True)
            print(f"   Step {step_id}: Tool call '{tool}' - {'✓ OK' if ok else '✗ FAILED'}")
            if not ok:
                print(f"           Error: {event.get('error', 'Unknown')}")
        
        elif edge_type == 'duplicate_tool_call_blocked':
            print(f"   Step {step_id}: Duplicate tool call blocked: {event.get('tool', '?')}")
    
    print("\n" + "=" * 70)
    print("DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print("""
Key Takeaways:
--------------
1. AgentSimToolRegistryAdapter bridges OperationEmulator → ToolRegistry
2. AgentSimAgentAdapter bridges BaseAgent (LLMAdapter) → LLMAgent  
3. SingleAgentRuntime works unchanged - it just uses the interfaces
4. The trace system captures all interactions for analysis

This pattern allows you to:
- Use any agent-sim scenario with your SingleAgentRuntime
- Swap different agents (LLM-based, rule-based, multi-agent orchestrators)
- Maintain full traceability and debugging capabilities
""")
    
    return result


if __name__ == "__main__":
    run_demo()
