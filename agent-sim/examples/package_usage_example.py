"""
Example: Using Agent Sim as an Installed Package

Demonstrates how to use agent_sim after installing via pip install -e .
"""

import agent_sim
from agent_sim import OperationEmulator
from agent_sim.core import ToolExecutor, HiddenState

# Import scenarios
from examples.scenarios import (
    EmailState,
    ContactsState,
    SMSState,
    CalendarState,
    SystemSettingsState,
    PhotoGalleryState,
    BrowserState,
    create_contacts_executor,
    create_sms_executor,
)


def test_basic_import():
    """Test that the package can be imported and used"""
    print(f"Agent Sim version: {agent_sim.__version__}")
    
    # Test creating tool executors for different mobile subjects
    contacts_tools = create_contacts_executor()
    sms_tools = create_sms_executor()
    print("✓ Mobile subject tool executors created")
    
    # Test state classes
    contacts_state = ContactsState()
    sms_state = SMSState()
    calendar_state = CalendarState()
    system_state = SystemSettingsState()
    photo_state = PhotoGalleryState()
    browser_state = BrowserState()
    email_state = EmailState()
    print("✓ Mobile state objects created")
    
    print("\n✅ All package functionality tests passed!")


if __name__ == "__main__":
    test_basic_import()
