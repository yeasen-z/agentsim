"""
Example: Using Agent Sim as an Installed Package

Demonstrates how to use agent_sim after installing via pip install -e .
"""

import agent_sim

# Import built-in scenarios from the installed package
from agent_sim.scenarios import (
    BrowserState,
    CalendarState,
    ContactsState,
    EmailState,
    PhotoGalleryState,
    SMSState,
    SystemSettingsState,
    create_contacts_executor,
    create_sms_executor,
)


def test_basic_import():
    """Test that the package can be imported and used"""
    print(f"Agent Sim version: {agent_sim.__version__}")

    # Test creating tool executors for different mobile subjects
    create_contacts_executor()
    create_sms_executor()
    print("✓ Mobile subject tool executors created")

    # Test state classes
    ContactsState()
    SMSState()
    CalendarState()
    SystemSettingsState()
    PhotoGalleryState()
    BrowserState()
    EmailState()
    print("✓ Mobile state objects created")

    print("\n✅ All package functionality tests passed!")


if __name__ == "__main__":
    test_basic_import()
