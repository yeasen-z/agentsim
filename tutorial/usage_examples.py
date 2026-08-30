"""
Agent Sim - Usage Examples

Demonstrates how to use the pluggable architecture to:
1. Load custom scenarios from modules
2. Create environment adapters for agents
3. Run agents with discovered tools and capabilities
"""

from agentsim import (
    EnvSim,
    ScenarioDefine,
    TaskDefine,
    as_env,
    registry,
)


def example_1_programmatic_registration():
    """Example 1: Programmatic scenario registration"""
    print("=" * 60)
    print("EXAMPLE 1: Programmatic Scenario Registration")
    print("=" * 60)

    # Import a scenario module
    from tutorial.scenarios.email_scenario import (
        compile_email_observation,
        init_email_state,
        register_email_tools,
    )

    # Register the scenario programmatically
    registry.register(
        id="email_demo",
        name="Email Demo",
        description="Simple email management demo",
        module="tutorial.scenarios.email_scenario",
        init_state=init_email_state,
        register_tools=register_email_tools,
        compile_observation=compile_email_observation,
        tags=["demo", "email"],
    )

    print(f"Registered scenarios: {registry.list()}")
    print()


def example_2_decorator_registration():
    """Example 2: Decorator-based registration"""
    print("=" * 60)
    print("EXAMPLE 2: Decorator-based Registration")
    print("=" * 60)

    # Import the scenario module - this triggers the decorator
    # We need to reload to trigger the decorator registration
    import importlib

    from tutorial.scenarios import email_scenario

    importlib.reload(email_scenario)  # Force re-execution of decorators

    print(f"Available scenarios after import: {registry.list_scenarios()}")

    # Show the decorator-registered scenario
    plugin = registry.get("email_management_v2")
    if plugin:
        print("\nDecorator-registered scenario found:")
        print(f"  ID: {plugin.id}")
        print(f"  Name: {plugin.name}")
        print(f"  Tags: {plugin.tags}")
    print()


def example_3_discover_environment():
    """Example 3: Agent discovers environment capabilities"""
    print("=" * 60)
    print("EXAMPLE 3: Agent Discovers Environment Capabilities")
    print("=" * 60)

    # Get a registered scenario - try email_demo first (from Example 1)
    plugin = registry.get("email_demo")
    if not plugin:
        plugin = registry.get("email_management_v2")
    if not plugin:
        plugin = registry.get("email_management")

    if not plugin:
        print("No email scenario available, skipping this example")
        return

    # Create the sim with scenario components
    from agentsim import ToolExecutor

    executor = ToolExecutor()
    plugin.register_tools(executor)

    scenario_def = ScenarioDefine(
        scenario_id=plugin.id, name=plugin.name, description=plugin.description, tasks=[]
    )

    sim = EnvSim(
        scenario=scenario_def,
        init_state=plugin.init_state,
        executor=executor,
        compile_obs=plugin.compile_observation,
    )

    # Create environment adapter (this is what agents interact with)
    env_adapter = as_env(sim)

    # Reset with a task
    task = TaskDefine(task_id="test_task", scenario=plugin.id, max_steps=10)

    env_adapter.reset(task, seed=42, instruction="Test task")

    # Agent discovers environment info
    env_info = env_adapter.info()

    print(f"\nEnvironment: {env_info.scenario_name}")
    print(f"Description: {env_info.description}")
    print(f"\nAvailable Tools ({len(env_info.tools)}):")
    for tool in env_info.tools:
        print(f"  - {tool.name}: {tool.description}")

    print("\nConstraints:")
    for constraint in env_info.constraints:
        print(f"  - {constraint}")

    print("\nCapabilities:")
    for cap in env_info.capabilities:
        print(f"  - {cap.name} ({cap.type}): {cap.description}")

    # Generate prompt for LLM agent
    print("\n--- Environment Prompt for Agent ---")
    print(env_info.to_prompt())
    print()


def example_4_agent_interaction():
    """Example 4: Agent interacts with environment through adapter"""
    print("=" * 60)
    print("EXAMPLE 4: Agent Interacts with Environment")
    print("=" * 60)

    plugin = registry.get("email_demo")
    if not plugin:
        plugin = registry.get("email_management_v2")
    if not plugin:
        plugin = registry.get("email_management")

    if not plugin:
        print("No email scenario available, skipping this example")
        return

    from agentsim import ScenarioDefine, TaskDefine, ToolExecutor

    # Setup sim
    executor = ToolExecutor()
    plugin.register_tools(executor)

    scenario_def = ScenarioDefine(
        scenario_id=plugin.id, name=plugin.name, description=plugin.description, tasks=[]
    )

    sim = EnvSim(
        scenario=scenario_def,
        init_state=plugin.init_state,
        executor=executor,
        compile_obs=plugin.compile_observation,
    )

    # Create adapter
    env_adapter = as_env(sim)

    # Reset environment
    task = TaskDefine(task_id="read_emails", scenario=plugin.id, max_steps=5)

    initial_obs = env_adapter.reset(task, seed=42, instruction="Read your emails")
    print(f"\nInitial observation: {initial_obs}")

    # Simulate agent actions
    print("\n--- Agent Actions ---")

    # Action 1: List emails
    result1 = env_adapter.call("list_emails", {"folder": "inbox"})
    print(f"\nAction 1 - list_emails: success={result1.success}")
    if result1.result:
        print(f"  Found {len(result1.result)} emails")
        for email in result1.result:
            print(f"    - {email['subject']} (from: {email['sender']})")

    # Action 2: Read first email
    if result1.result and len(result1.result) > 0:
        email_id = result1.result[0]["id"]
        result2 = env_adapter.call("read_email", {"email_id": email_id})
        print(f"\nAction 2 - read_email: success={result2.success}")
        if result2.result:
            print(f"  Subject: {result2.result['subject']}")
            print(f"  Body: {result2.result['body'][:50]}...")

    # Check if done
    print(f"\nEpisode done: {env_adapter.done()}")
    print(f"Episode result: {env_adapter.result()}")
    print()


def example_5_yaml_configuration():
    """Example 5: Loading scenarios from YAML configuration"""
    print("=" * 60)
    print("EXAMPLE 5: YAML Configuration (Conceptual)")
    print("=" * 60)

    yaml_example = """
# scenarios.yaml
scenarios:
  - id: file_management
    name: File Management
    description: Manage files in a virtual filesystem
    module: scenarios.filesystem
    entrypoint: setup
    tags: [files, system]

  - id: calendar_mgmt
    name: Calendar Management
    description: Manage calendar events and meetings
    module: scenarios.calendar
    entrypoint: setup
    tags: [calendar, productivity]
"""

    print("YAML Configuration Format:")
    print(yaml_example)
    print("\nTo load from YAML:")
    print("  registry.load_yaml('scenarios.yaml', base_module='my_package')")
    print()


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("AGENT SIM - PLUGGABLE ARCHITECTURE EXAMPLES")
    print("=" * 60 + "\n")

    # Run examples
    example_1_programmatic_registration()
    example_2_decorator_registration()
    example_3_discover_environment()
    example_4_agent_interaction()
    example_5_yaml_configuration()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
