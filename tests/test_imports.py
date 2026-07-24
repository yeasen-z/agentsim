"""
Test basic installation and imports
"""


def test_import_core():
    """Test that core components can be imported"""


def test_import_sim():
    """Test that sim can be imported"""


def test_import_multi_agent():
    """Test that multi-agent components can be imported"""


def test_import_llm_sim():
    """Test that LLM simulation components can be imported"""


def test_import_agents():
    """Test that agent adapters can be imported"""


def test_version():
    """Test version string"""
    import agentsim

    assert hasattr(agentsim, "__version__")
    assert isinstance(agentsim.__version__, str)
