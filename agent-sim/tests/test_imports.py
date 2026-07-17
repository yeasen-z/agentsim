"""
Test basic installation and imports
"""
import pytest


def test_import_core():
    """Test that core components can be imported"""
    from agent_sim.core import (
        HiddenState,
        EntityState,
        ToolDefinition,
        ToolResult,
        ToolCall,
        ToolExecutor,
        ToolRiskLevel,
        TaskDefinition,
        ScenarioDefinition,
        Verifier,
        VerificationResult,
        Trace,
        Registry,
        EnvironmentInterface,
    )
    

def test_import_emulator():
    """Test that emulator can be imported"""
    from agent_sim import OperationEmulator
    

def test_import_multi_agent():
    """Test that multi-agent components can be imported"""
    from agent_sim.multi_agent import (
        AgentRole,
        BaseAgent,
        MultiAgentOrchestrator,
    )


def test_import_llm_sim():
    """Test that LLM simulation components can be imported"""
    from agent_sim.llm_sim import (
        InstructionGenerator,
        UserSimulator,
    )


def test_import_agents():
    """Test that agent adapters can be imported"""
    from agent_sim.agents import (
        LLMClient,
        MockLLMClient,
        LLMAdapter,
    )


def test_version():
    """Test version string"""
    import agent_sim
    assert hasattr(agent_sim, '__version__')
    assert isinstance(agent_sim.__version__, str)
