"""
Test basic installation and imports
"""


def test_import_core():
    """Test that core components can be imported"""


def test_import_emulator():
    """Test that emulator can be imported"""


def test_import_multi_agent():
    """Test that multi-agent components can be imported"""


def test_import_llm_sim():
    """Test that LLM simulation components can be imported"""


def test_import_agents():
    """Test that agent adapters can be imported"""


def test_import_builtin_scenarios():
    """Test that built-in scenarios are part of the installed package."""
    from agent_sim.scenarios import (
        BrowserState,
        CalendarState,
        ClipboardState,
        ContactsState,
        EmailState,
        PhotoGalleryState,
        SMSState,
        SystemSettingsState,
    )

    assert all(
        scenario is not None
        for scenario in (
            BrowserState,
            CalendarState,
            ClipboardState,
            ContactsState,
            EmailState,
            PhotoGalleryState,
            SMSState,
            SystemSettingsState,
        )
    )


def test_version():
    """Test version string"""
    import agent_sim

    assert hasattr(agent_sim, "__version__")
    assert isinstance(agent_sim.__version__, str)
