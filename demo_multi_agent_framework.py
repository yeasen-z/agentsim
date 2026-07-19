"""
Agent-Sim Framework Demo: Multi-Agent Collaboration with Trace Monitoring

Architecture:
1. Core Environment (The Framework): Manages state, tools, and Trace monitoring.
2. Pluggable Agents: Independent logic units (Planner, Executor).
3. Pluggable Runtime: The "Brain" that schedules agents and manages flow.
"""

from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# ==============================================================================
# 1. Core Data Structures & Interfaces (The Framework Contract)
# ==============================================================================


class ActionType(str, Enum):
    CALL_TOOL = "call_tool"
    SEND_MESSAGE = "send_message"  # For multi-agent communication
    RETURN_RESULT = "return_result"
    WAIT = "wait"  # Yield control to other agents


@dataclass
class AgentAction:
    action_type: ActionType
    tool: Optional[str] = None
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Optional[str] = None
    target_agent: Optional[str] = None  # For send_message
    message: Optional[str] = None  # For send_message

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type.value,
            "tool": self.tool,
            "arguments": self.arguments,
            "result": self.result,
            "target_agent": self.target_agent,
            "message": self.message,
        }


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]


@dataclass
class ToolResult:
    success: bool
    output: Any
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {"success": self.success, "output": self.output, "error": self.error}


# --- Framework Interfaces ---


class IAgent(ABC):
    """Interface for any Agent implementation."""

    @property
    @abstractmethod
    def agent_id(self) -> str:
        pass

    @property
    @abstractmethod
    def role_description(self) -> str:
        pass

    @abstractmethod
    def decide(self, global_state: Dict[str, Any], inbox: List[Dict]) -> AgentAction:
        """Based on state and messages, decide next action."""
        pass


class IRuntime(ABC):
    """Interface for any Runtime/Scheduler implementation."""

    @abstractmethod
    def run(self, agents: List[IAgent], environment: "Environment") -> Dict[str, Any]:
        """Orchestrate the agents until completion."""
        pass


class IToolRegistry(ABC):
    """Interface for Tool execution."""

    @abstractmethod
    def get_specs(self) -> List[ToolSpec]:
        pass

    @abstractmethod
    def invoke(self, name: str, args: Dict[str, Any]) -> ToolResult:
        pass


# ==============================================================================
# 2. Core Environment Implementation (The "Sim" Part)
# ==============================================================================


class TraceMonitor:
    """
    The Heart of the Framework: Records every interaction, decision, and state change.
    This is independent of specific Agents or Runtimes.
    """

    def __init__(self):
        self.trace_log: List[Dict[str, Any]] = []
        self.start_time = time.time()

    def record(self, event_type: str, details: Dict[str, Any]):
        entry = {"timestamp": time.time() - self.start_time, "event_type": event_type, **details}
        self.trace_log.append(entry)
        print(
            f"[TRACE] {entry['timestamp']:.2f}s | {event_type}: {json.dumps(details, default=str)[:100]}..."
        )

    def get_report(self) -> Dict[str, Any]:
        return {
            "total_events": len(self.trace_log),
            "duration": time.time() - self.start_time,
            "log": self.trace_log,
        }


class SimpleToolRegistry(IToolRegistry):
    """Concrete implementation of tools for the demo."""

    def __init__(self):
        self.tools = {
            "search_web": ToolSpec("search_web", "Search the internet", {"query": "string"}),
            "calculate": ToolSpec("calculate", "Perform math", {"expression": "string"}),
            "write_file": ToolSpec(
                "write_file", "Save content to file", {"filename": "string", "content": "string"}
            ),
        }

    def get_specs(self) -> List[ToolSpec]:
        return list(self.tools.values())

    def invoke(self, name: str, args: Dict[str, Any]) -> ToolResult:
        if name not in self.tools:
            return ToolResult(False, None, f"Tool {name} not found")

        # Mock implementations
        if name == "search_web":
            return ToolResult(True, f"Search results for '{args.get('query')}': [Link1, Link2]")
        elif name == "calculate":
            try:
                # Dangerous in prod, safe for demo
                res = eval(args.get("expression", "0"))
                return ToolResult(True, res)
            except Exception as e:
                return ToolResult(False, None, str(e))
        elif name == "write_file":
            return ToolResult(True, f"File '{args.get('filename')}' written successfully.")

        return ToolResult(False, None, "Not implemented")


class Environment:
    """
    The Core Framework Container.
    Holds State, Tools, and the Trace Monitor.
    """

    def __init__(self):
        self.shared_state: Dict[str, Any] = {
            "messages": {},  # agent_id -> [messages]
            "global_context": {},
            "step_count": 0,
        }
        self.tool_registry = SimpleToolRegistry()
        self.trace_monitor = TraceMonitor()

    def get_inbox(self, agent_id: str) -> List[Dict]:
        return self.shared_state["messages"].get(agent_id, [])

    def send_message(self, from_agent: str, to_agent: str, content: str):
        if to_agent not in self.shared_state["messages"]:
            self.shared_state["messages"][to_agent] = []
        msg = {"from": from_agent, "content": content}
        self.shared_state["messages"][to_agent].append(msg)
        self.trace_monitor.record(
            "message_sent", {"from": from_agent, "to": to_agent, "content": content}
        )

    def clear_inbox(self, agent_id: str):
        self.shared_state["messages"][agent_id] = []

    def execute_tool(self, name: str, args: Dict[str, Any]) -> ToolResult:
        self.trace_monitor.record("tool_invocation_start", {"tool": name, "args": args})
        result = self.tool_registry.invoke(name, args)
        self.trace_monitor.record("tool_invocation_end", {"tool": name, "success": result.success})
        return result


# ==============================================================================
# 3. Pluggable Agent Implementations
# ==============================================================================


class PlannerAgent(IAgent):
    """Agent that breaks down tasks and delegates."""

    @property
    def agent_id(self) -> str:
        return "planner"

    @property
    def role_description(self) -> str:
        return "Task Decomposer & Strategist"

    def decide(self, global_state: Dict[str, Any], inbox: List[Dict]) -> AgentAction:
        # Check if executor finished (read inbox first!)
        for msg in inbox:
            if "done" in msg["content"].lower() or "complete" in msg["content"].lower():
                return AgentAction(
                    action_type=ActionType.RETURN_RESULT, result="Task completed by team!"
                )

        # If no plan created yet, send initial task
        if not global_state.get("plan_created"):
            global_state["plan_created"] = True  # Mark as created
            return AgentAction(
                action_type=ActionType.SEND_MESSAGE,
                target_agent="executor",
                message="Please calculate 25 * 4 and save the result to 'result.txt'.",
            )

        # Otherwise wait
        return AgentAction(action_type=ActionType.WAIT)


class ExecutorAgent(IAgent):
    """Agent that executes specific steps."""

    @property
    def agent_id(self) -> str:
        return "executor"

    @property
    def role_description(self) -> str:
        return "Tool User & Worker"

    def decide(self, global_state: Dict[str, Any], inbox: List[Dict]) -> AgentAction:
        # If no task, wait
        if not inbox:
            return AgentAction(action_type=ActionType.WAIT)

        last_msg = inbox[-1]["content"]

        if "calculate" in last_msg and "save" in last_msg:
            # Step 1: Calculate
            if not global_state.get("calc_done"):
                return AgentAction(
                    action_type=ActionType.CALL_TOOL,
                    tool="calculate",
                    arguments={"expression": "25 * 4"},
                )

            # Step 2: Write File (Mocking state check for simplicity)
            if global_state.get("calc_done") and not global_state.get("file_written"):
                return AgentAction(
                    action_type=ActionType.CALL_TOOL,
                    tool="write_file",
                    arguments={"filename": "result.txt", "content": "100"},
                )

            # Step 3: Report back
            return AgentAction(
                action_type=ActionType.SEND_MESSAGE,
                target_agent="planner",
                message="Calculation and file write done. Task complete.",
            )

        return AgentAction(action_type=ActionType.WAIT)


# ==============================================================================
# 4. Pluggable Runtime Implementation (Multi-Agent Scheduler)
# ==============================================================================


class RoundRobinRuntime(IRuntime):
    """
    A simple Multi-Agent Runtime.
    Strategy: Round-robin scheduling, stops when any agent returns a result.
    """

    def __init__(self, max_steps: int = 10):
        self.max_steps = max_steps

    def run(self, agents: List[IAgent], environment: Environment) -> Dict[str, Any]:
        {a.agent_id: a for a in agents}
        step = 0

        environment.trace_monitor.record("runtime_start", {"agents": [a.agent_id for a in agents]})

        while step < self.max_steps:
            step += 1
            environment.shared_state["step_count"] = step
            made_progress = False

            for agent in agents:
                # 1. Get Inbox
                inbox = environment.get_inbox(agent.agent_id)

                # 2. Agent Decides
                action = agent.decide(environment.shared_state, inbox)

                # 3. Record Decision
                environment.trace_monitor.record(
                    "agent_action", {"agent": agent.agent_id, "action": action.to_dict()}
                )

                # 4. Execute Action
                if action.action_type == ActionType.RETURN_RESULT:
                    environment.trace_monitor.record("runtime_end", {"status": "success"})
                    return {"status": "finished", "result": action.result, "steps": step}

                elif action.action_type == ActionType.CALL_TOOL:
                    environment.execute_tool(action.tool, action.arguments)
                    # Update shared state based on tool result (Mock logic for demo)
                    if action.tool == "calculate":
                        environment.shared_state["calc_done"] = True
                    if action.tool == "write_file":
                        environment.shared_state["file_written"] = True
                    made_progress = True

                elif action.action_type == ActionType.SEND_MESSAGE:
                    environment.send_message(agent.agent_id, action.target_agent, action.message)
                    made_progress = True

                # Only clear inbox if agent chose WAIT (meaning it processed what it needed)
                # This allows agents to keep processing messages across multiple turns if they take tool actions
                if action.action_type == ActionType.WAIT and inbox:
                    environment.clear_inbox(agent.agent_id)

            if not made_progress and step > 1:
                # Prevent infinite loop if everyone waits
                break

        return {"status": "max_steps_reached", "steps": step}


# ==============================================================================
# 5. Demo Execution
# ==============================================================================


def run_demo():
    print("=" * 60)
    print("STARTING MULTI-AGENT FRAMEWORK DEMO")
    print("=" * 60)

    # 1. Setup Environment (The Core)
    env = Environment()

    # 2. Instantiate Pluggable Agents
    planner = PlannerAgent()
    executor = ExecutorAgent()
    agents = [planner, executor]

    # 3. Instantiate Pluggable Runtime
    runtime = RoundRobinRuntime(max_steps=8)

    # 4. Run!
    final_result = runtime.run(agents, env)

    # 5. Output Results
    print("\n" + "=" * 60)
    print("FINAL RESULT:")
    print(json.dumps(final_result, indent=2))

    print("\n" + "=" * 60)
    print("TRACE REPORT (The Monitoring Core):")
    report = env.trace_monitor.get_report()
    print(f"Total Events: {report['total_events']}")
    print(f"Duration: {report['duration']:.4f}s")
    print("\n--- Event Log ---")
    for event in report["log"]:
        # Filter verbose logs for readability
        if event["event_type"] not in ["tool_invocation_end"]:
            print(
                f"[{event['timestamp']:.2f}s] {event['event_type']} -> {event.get('agent') or event.get('from') or 'SYSTEM'} : {str(event.get('action') or event.get('content') or event.get('tool'))[:50]}"
            )


if __name__ == "__main__":
    run_demo()
