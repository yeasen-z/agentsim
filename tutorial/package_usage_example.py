"""Repository example using Agent Sim with the toy environment pack."""

import agentsim

# Import toy environments from the repository examples
from tutorial.scenarios import (
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
    print(f"Agent Sim version: {agentsim.__version__}")

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
