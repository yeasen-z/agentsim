"""
Agent Sim - Scenarios Package

Mobile and desktop environment scenarios for agent simulation.
"""

# Email scenario (full scenario with state, tools, verifier)
from .email_scenario import (
    EmailState,
    init_email_state,
    register_email_tools,
    create_email_verifier,
    setup as setup_email_scenario,
)

# Clipboard scenario
from .clipboard_scenario import (
    ClipboardState,
    register_clipboard_tools,
    create_clipboard_executor,
)

# Mobile phone task subjects
from .contacts_subject import ContactsState, create_contacts_executor
from .sms_subject import SMSState, create_sms_executor
from .calendar_subject import CalendarState, create_calendar_executor
from .system_settings_subject import SystemSettingsState, create_system_settings_executor
from .photo_gallery_subject import PhotoGalleryState, create_photo_gallery_executor
from .browser_subject import BrowserState, create_browser_executor

__all__ = [
    # Email scenario
    "EmailState",
    "init_email_state",
    "register_email_tools",
    "create_email_verifier",
    "setup_email_scenario",
    
    # Clipboard scenario
    "ClipboardState", 
    "register_clipboard_tools",
    "create_clipboard_executor",
    
    # Mobile subjects
    "ContactsState",
    "create_contacts_executor",
    "SMSState",
    "create_sms_executor",
    "CalendarState",
    "create_calendar_executor",
    "SystemSettingsState",
    "create_system_settings_executor",
    "PhotoGalleryState",
    "create_photo_gallery_executor",
    "BrowserState",
    "create_browser_executor",
]
