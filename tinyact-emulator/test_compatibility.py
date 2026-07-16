"""
Test script demonstrating single-agent and multi-agent compatibility.
"""

from tinyact import (
    OperationEmulator,
    HiddenState,
    ToolExecutor,
    ToolDefinition,
    ToolRiskLevel,
    Verifier,
    TaskDefinition,
    ScenarioDefinition,
    create_agent,
    create_orchestrator,
    AgentRole,
    MockLLMClient,
    LLMAdapter,
)


def create_simple_scenario():
    """Create a simple test scenario."""
    return ScenarioDefinition(
        scenario_id="test_ops",
        name="Test Operations",
        description="A simple test scenario",
        state_schema=["items"],
        tools={
            "read": ["get_item"],
            "write": ["set_item"],
        },
        tasks=["test_task_001"]
    )


def create_state_initializer(initial_data: dict):
    """Create a state initializer function."""
    def initialize(state_config: dict, seed: int) -> HiddenState:
        state = HiddenState()
        state.metadata = {"seed": seed}
        state.entities = {
            "items": initial_data.get("items", [])
        }
        state.files = initial_data.get("files", {})
        return state
    return initialize


def create_test_tools():
    """Create test tool executor."""
    executor = ToolExecutor()
    
    # Define tool functions
    def get_item_func(state, item_id: str):
        items = state.entities.get("items", [])
        for item in items:
            if item.id == item_id:
                return {"found": True, "item": item.to_dict()}
        return {"found": False, "error": "Item not found"}
    
    def set_item_func(state, item_id: str, value: str):
        items = state.entities.get("items", [])
        for item in items:
            if item.id == item_id:
                item.value = value
                return {"success": True, "item_id": item_id}
        
        # Create new item
        from tinyact.core import EntityState
        class Item(EntityState):
            def __init__(self, id, value):
                self.id = id
                self.value = value
        
        new_item = Item(id=item_id, value=value)
        items.append(new_item)
        state.entities["items"] = items
        return {"success": True, "item_id": item_id, "created": True}
    
    # Register tools with definitions
    executor.register_tool(
        "get_item",
        get_item_func,
        ToolDefinition(
            name="get_item",
            description="Get an item by ID",
            parameters={"type": "object", "properties": {"item_id": {"type": "string"}}},
            risk_level=ToolRiskLevel.SAFE,
            category="read"
        )
    )
    executor.register_tool(
        "set_item",
        set_item_func,
        ToolDefinition(
            name="set_item",
            description="Set or create an item",
            parameters={"type": "object", "properties": {"item_id": {"type": "string"}, "value": {"type": "string"}}},
            risk_level=ToolRiskLevel.MODERATE,
            category="write"
        )
    )
    
    return executor


def test_single_agent():
    """Test single agent execution."""
    print("\n=== Testing Single Agent ===")
    
    # Setup
    scenario = create_simple_scenario()
    state_init = create_state_initializer({"items": []})
    tools = create_test_tools()
    verifier = Verifier()
    
    emulator = OperationEmulator(
        scenario=scenario,
        state_initializer=state_init,
        tool_executor=tools,
        verifier=verifier
    )
    
    # Create task
    task = TaskDefinition(
        task_id="test_task_001",
        scenario="test_ops",
        hidden_goal={"action": "set_item", "item_id": "item1", "value": "test_value"},
        max_steps=5
    )
    
    # Create single agent with mock LLM
    mock_responses = [
        '{"tool": "set_item", "args": {"item_id": "item1", "value": "test_value"}}',
        '{"tool": "finish", "args": {}}'
    ]
    llm_client = MockLLMClient(responses=mock_responses)
    agent = LLMAdapter(llm_client=llm_client, agent_id="test_single_agent")
    
    # Run episode
    observation = emulator.reset(task=task, seed=42, instruction="Set item1 to test_value")
    print(f"Initial observation: {observation}")
    
    for step in range(5):
        tool_name, args = agent.act(
            instruction=emulator.instruction,
            observation=observation,
            available_tools=emulator.available_tools()
        )
        
        if not tool_name or tool_name == "finish":
            print("Agent finished.")
            break
        
        print(f"Step {step+1}: Agent calls {tool_name}({args})")
        result = emulator.call_tool(tool_name, args)
        print(f"Result: {result.message}")
        
        if emulator.is_done():
            break
        
        observation = emulator.observe()
    
    final_result = emulator.get_final_result()
    print(f"Final result: {final_result}")
    
    emulator.end_episode()
    print("Single agent test completed.\n")


def test_multi_agent_sequential():
    """Test multi-agent sequential collaboration."""
    print("\n=== Testing Multi-Agent (Sequential) ===")
    
    # Create agents
    manager = create_agent("manager", agent_id="manager_001")
    worker = create_agent("worker", agent_id="worker_001")
    reviewer = create_agent("reviewer", agent_id="reviewer_001")
    
    # Create orchestrator
    orchestrator = create_orchestrator(mode="sequential", agents=[manager, worker, reviewer])
    
    print(f"Created orchestrator with {len(orchestrator.get_agents())} agents")
    print(f"Agents: {[a.agent_id for a in orchestrator.get_agents()]}")
    
    # Test agent selection
    for i in range(6):
        next_agent = orchestrator.select_next_agent()
        if next_agent:
            print(f"Turn {i+1}: {next_agent.agent_id} ({next_agent.role.value})")
    
    print("Multi-agent sequential test completed.\n")


def test_multi_agent_hierarchical():
    """Test multi-agent hierarchical collaboration."""
    print("\n=== Testing Multi-Agent (Hierarchical) ===")
    
    # Create agents
    manager = create_agent("manager", agent_id="boss")
    worker1 = create_agent("worker", agent_id="worker_A")
    worker2 = create_agent("worker", agent_id="worker_B")
    
    # Create orchestrator
    orchestrator = create_orchestrator(mode="hierarchical", agents=[manager, worker1, worker2])
    
    print(f"Created hierarchical orchestrator")
    print(f"Manager: {manager.agent_id}")
    print(f"Workers: {[worker1.agent_id, worker2.agent_id]}")
    
    # Test agent selection - manager should go first
    first = orchestrator.select_next_agent()
    print(f"First turn: {first.agent_id} (should be manager)")
    
    # Then workers
    second = orchestrator.select_next_agent()
    print(f"Second turn: {second.agent_id} (should be worker)")
    
    print("Multi-agent hierarchical test completed.\n")


def test_agent_roles():
    """Test different agent roles."""
    print("\n=== Testing Agent Roles ===")
    
    roles = [
        ("single", "Single Agent"),
        ("manager", "Manager Agent"),
        ("worker", "Worker Agent"),
        ("reviewer", "Reviewer Agent"),
    ]
    
    for role_type, description in roles:
        agent = create_agent(role_type, agent_id=f"{role_type}_001")
        print(f"{description}: ID={agent.agent_id}, Role={agent.role.value}")
    
    print("Agent roles test completed.\n")


if __name__ == "__main__":
    print("=" * 60)
    print("TinyAct Emulator - Single & Multi-Agent Compatibility Test")
    print("=" * 60)
    
    test_agent_roles()
    test_single_agent()
    test_multi_agent_sequential()
    test_multi_agent_hierarchical()
    
    print("=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)
