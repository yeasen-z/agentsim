"""
Example: Implementing a Custom Runtime for agent-sim

This example demonstrates how to implement your own Runtime that works
with the agent-sim framework by following the standard interfaces.
"""

from typing import Any, Dict, List

from agent_sim.core.interfaces import (
    Action,
    AgentInterface,
    EnvironmentInterface,
    ExecutionResult,
)


class SimpleSingleAgentRuntime:
    """
    A simple single-agent runtime implementation.

    This runtime:
    1. Resets the environment
    2. Loops: observe → agent.decide() → execute action
    3. Terminates when: max_steps, agent returns result, or verification succeeds/fails
    4. Records all interactions in the environment's trace monitor
    """

    def __init__(self, max_steps: int = 10):
        self.max_steps = max_steps

    def run(
        self, env: EnvironmentInterface, agent: AgentInterface, config: Dict[str, Any] = None
    ) -> ExecutionResult:
        """
        Run an agent in the environment.

        This is the main execution loop that:
        1. Initializes the episode
        2. Repeats: observe → decide → act
        3. Returns final result with trace
        """
        config = config or {}
        instruction = config.get("instruction", "Complete the task")
        task_id = config.get("task_id", "default_task")
        seed = config.get("seed", 42)

        # Reset both environment and agent
        env.reset(task_id=task_id, seed=seed, instruction=instruction)
        agent.reset()

        # Get initial observation
        observation = env.observe()
        available_tools = env.get_tools()

        step_count = 0
        action_history: List[Action] = []

        # Main execution loop
        while step_count < self.max_steps:
            step_count += 1

            # Agent decides on action
            action = agent.decide(
                observation=observation,
                available_tools=available_tools,
                context={"step": step_count, "history": action_history},
            )

            # Record action
            action_history.append(action)

            # Execute action through environment
            if action.action_type == "call_tool":
                # Call tool through environment
                result = env.call_tool(tool_name=action.tool_name, args=action.arguments)

                # Get new observation
                observation = env.observe()

                # Check if we should continue
                if not result.success:
                    # Tool failed - agent might want to try something else
                    continue

            elif action.action_type == "return_result":
                # Agent wants to finish
                break

            elif action.action_type == "textual":
                # Textual action (thinking, etc.) - just continue
                continue

            # Check verification
            verification = env.verify()
            if verification.get("success") or verification.get("failed"):
                break

        # Get final verification
        final_verification = env.verify()

        # Get trace from environment monitor
        trace = env.get_trace()
        trace_available = trace is not None

        # Determine status
        if final_verification.get("success"):
            status = "success"
        elif final_verification.get("failed"):
            status = "failed"
        elif step_count >= self.max_steps:
            status = "max_steps_reached"
        else:
            status = "finished"

        return ExecutionResult(
            status=status,
            result=final_verification.get("reason", ""),
            steps_taken=step_count,
            trace_available=trace_available,
            metadata={
                "verification": final_verification,
                "actions": [a.to_dict() for a in action_history],
            },
        )


class HumanInLoopRuntime:
    """
    Example of a custom runtime with human feedback.

    This runtime pauses at each step to get human input before executing.
    Useful for debugging, training, or safety-critical applications.
    """

    def __init__(self, max_steps: int = 10, require_approval: bool = True):
        self.max_steps = max_steps
        self.require_approval = require_approval

    def run(
        self, env: EnvironmentInterface, agent: AgentInterface, config: Dict[str, Any] = None
    ) -> ExecutionResult:
        """Run with human-in-the-loop."""
        config = config or {}

        # Initialize
        env.reset(
            task_id=config.get("task_id", "default"),
            seed=config.get("seed", 42),
            instruction=config.get("instruction", ""),
        )
        agent.reset()

        observation = env.observe()
        available_tools = env.get_tools()

        step_count = 0

        print(f"\n{'='*60}")
        print("HUMAN-IN-THE-LOOP RUNTIME STARTED")
        print(f"{'='*60}\n")

        while step_count < self.max_steps:
            step_count += 1

            # Agent decides
            action = agent.decide(
                observation=observation,
                available_tools=available_tools,
                context={"step": step_count},
            )

            print(f"\n--- Step {step_count} ---")
            print(f"Agent wants to: {action.action_type}")
            if action.tool_name:
                print(f"Tool: {action.tool_name}")
                print(f"Arguments: {action.arguments}")

            # Human approval
            if self.require_approval and action.action_type == "call_tool":
                approval = input("\nExecute this action? (y/n/skip): ").lower()
                if approval == "n":
                    print("Action cancelled by human.")
                    continue
                elif approval == "skip":
                    print("Skipping to next step.")
                    step_count -= 1  # Don't count skipped steps
                    continue

            # Execute
            if action.action_type == "call_tool":
                result = env.call_tool(tool_name=action.tool_name, args=action.arguments)
                observation = env.observe()
                print(f"Result: {result}")

            elif action.action_type == "return_result":
                print(f"\nAgent finished with result: {action.result}")
                break

            # Check done
            verification = env.verify()
            if verification.get("success") or verification.get("failed"):
                print(f"\nVerification: {verification}")
                break

        # Final result
        trace = env.get_trace()
        verification = env.verify()

        status = "success" if verification.get("success") else "failed"

        print(f"\n{'='*60}")
        print(f"RUNTIME FINISHED - Status: {status}")
        print(f"Steps taken: {step_count}")
        print(f"Trace available: {trace is not None}")
        print(f"{'='*60}\n")

        return ExecutionResult(
            status=status,
            result=verification.get("reason", ""),
            steps_taken=step_count,
            trace_available=trace is not None,
            metadata={"verification": verification},
        )


# ============================================================================
# Usage Example
# ============================================================================


def demo_custom_runtime():
    """Demonstrate using a custom runtime with agent-sim."""

    print(
        """
    ╔══════════════════════════════════════════════════════════╗
    ║  Custom Runtime Example for Agent-Sim Framework         ║
    ╚══════════════════════════════════════════════════════════╝

    This example shows how to implement and use custom Runtimes
    that work with the agent-sim environment framework.

    Key Points:
    -----------
    1. Implement RuntimeInterface.run() method
    2. Use EnvironmentInterface to interact with environment
    3. Use AgentInterface to get decisions from agent
    4. Trace is automatically recorded by the environment
    5. Return ExecutionResult with status and metadata

    Benefits:
    ---------
    ✓ Swap different Runtimes without changing environment
    ✓ Add custom logic (human approval, RL training, etc.)
    ✓ Full control over execution flow
    ✓ Access to complete trace for analysis
    """
    )

    # Example 1: Simple runtime
    print("\n" + "=" * 60)
    print("Example 1: SimpleSingleAgentRuntime")
    print("=" * 60)

    runtime1 = SimpleSingleAgentRuntime(max_steps=5)
    print(f"✓ Created runtime with max_steps={runtime1.max_steps}")
    print("✓ Implements RuntimeInterface")
    print("✓ Can be used with any EnvironmentInterface + AgentInterface")

    # Example 2: Human-in-loop runtime
    print("\n" + "=" * 60)
    print("Example 2: HumanInLoopRuntime")
    print("=" * 60)

    HumanInLoopRuntime(max_steps=5, require_approval=True)
    print("✓ Created runtime with human approval")
    print("✓ Pauses at each step for human input")
    print("✓ Useful for debugging and safety-critical tasks")

    # Example 3: What you could build
    print("\n" + "=" * 60)
    print("What You Could Build:")
    print("=" * 60)
    print(
        """
    - MultiAgentRuntime: Coordinate multiple agents
    - RLTrainingRuntime: Train agents with reinforcement learning
    - BatchRuntime: Run multiple episodes in parallel
    - CurriculumRuntime: Progressive difficulty increase
    - SafetyRuntime: Add safety checks before execution
    - DebugRuntime: Step-through debugging with breakpoints
    """
    )

    print("\n" + "=" * 60)
    print("See ARCHITECTURE_REDESIGN.md for full details")
    print("=" * 60)


if __name__ == "__main__":
    demo_custom_runtime()
