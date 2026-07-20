"""
Test Mobile Phone Task Subjects

Tests for contacts, SMS, calendar, system settings, photo gallery, and browser subjects.
"""

from datetime import datetime, timedelta

from agent_sim.scenarios.browser_subject import BrowserState, create_browser_executor
from agent_sim.scenarios.calendar_subject import CalendarTools
from agent_sim.scenarios.contacts_subject import ContactsTools
from agent_sim.scenarios.photo_gallery_subject import (
    PhotoGalleryState,
    create_photo_gallery_executor,
)
from agent_sim.scenarios.sms_subject import SMSTools
from agent_sim.scenarios.system_settings_subject import (
    SystemSettingsState,
    create_system_settings_executor,
)


def test_contacts():
    """Test contacts functionality"""
    print("=" * 50)
    print("Testing Contacts Functionality")
    print("=" * 50)

    contacts = ContactsTools()

    # 1. Create groups
    print("\n1. Creating groups...")
    work_group = contacts.create_group("Work")
    print(f"   Created group: {work_group}")

    family_group = contacts.create_group("Family")
    print(f"   Created group: {family_group}")

    # 2. Add contacts
    print("\n2. Adding contacts...")
    contact1 = contacts.add_contact(
        name="John Doe",
        phone="13800138001",
        email="john@example.com",
        company="ABC Corp",
        groups=["Work"],
    )
    print(f"   Added contact: {contact1['name']} - {contact1['phone']}")

    contact2 = contacts.add_contact(
        name="Jane Smith", phone="13800138002", email="jane@example.com", groups=["Work"]
    )
    print(f"   Added contact: {contact2['name']} - {contact2['phone']}")

    contact3 = contacts.add_contact(name="Bob Wilson", phone="13800138003", groups=["Family"])
    print(f"   Added contact: {contact3['name']} - {contact3['phone']}")

    # 3. List all contacts
    print("\n3. Listing all contacts...")
    all_contacts = contacts.list_contacts()
    print(f"   Total contacts: {len(all_contacts)}")
    for c in all_contacts:
        print(f"      - {c['name']} ({c['phone']})")

    # 4. Search contacts (using list_contacts with query parameter)
    print("\n4. Searching contacts...")
    search_result = contacts.list_contacts(query="John")
    print(f"   Found {len(search_result)} contact(s) matching 'John'")

    # 5. Get contacts by group (using list_contacts with group parameter)
    print("\n5. Getting contacts by group...")
    work_contacts = contacts.list_contacts(group="Work")
    print(f"   Work group has {len(work_contacts)} contact(s)")

    # 6. Update contact
    print("\n6. Updating contact...")
    updated = contacts.update_contact(contact1["id"], email="john.doe@newcorp.com")
    print(f"   Updated email: {updated['email']}")

    # 7. Delete contact
    print("\n7. Deleting contact...")
    contacts.delete_contact(contact3["id"])
    remaining = contacts.list_contacts()
    print(f"   Remaining contacts: {len(remaining)}")

    print("\n✓ Contacts functionality test passed!\n")


def test_sms():
    """Test SMS functionality"""
    print("=" * 50)
    print("Testing SMS Functionality")
    print("=" * 50)

    sms = SMSTools()

    # 1. Send messages
    print("\n1. Sending messages...")
    msg1 = sms.send_message("13800138001", "Hello, this is a test message!")
    print(f"   Sent to: {msg1['receiver']}")

    msg2 = sms.send_message("13800138002", "Meeting at 3 PM today.")
    print(f"   Sent to: {msg2['receiver']}")

    msg3 = sms.send_message("13800138001", "Please confirm receipt.")
    print(f"   Sent to: {msg3['receiver']}")

    # 2. List conversations
    print("\n2. Listing conversations...")
    conversations = sms.list_conversations()
    print(f"   Total conversations: {len(conversations)}")
    for conv in conversations:
        print(f"      - {conv['phone_number']}: {conv['total_count']} messages")

    # 3. Get conversation messages
    print("\n3. Getting conversation messages...")
    messages = sms.list_messages("13800138001")
    print(f"   Messages with 13800138001: {len(messages)}")
    for msg in messages:
        print(f"      [{msg['direction']}] {msg['content']}")

    # 4. Mark as read
    print("\n4. Marking messages as read...")
    # Get a message ID to mark as read
    messages = sms.list_messages("13800138001")
    if messages:
        sms.mark_as_read(messages[0]["id"])
        print(f"   Marked message {messages[0]['id']} as read")

    # 5. Delete conversation
    print("\n5. Deleting conversation...")
    sms.delete_conversation("13800138002")
    remaining = sms.list_conversations()
    print(f"   Remaining conversations: {len(remaining)}")

    # 6. Get stats
    print("\n6. Getting statistics...")
    all_messages = sms.list_messages()
    unread_count = sum(1 for m in all_messages if not m["is_read"])
    print(f"   Total messages: {len(all_messages)}")
    print(f"   Unread count: {unread_count}")

    print("\n✓ SMS functionality test passed!\n")


def test_calendar():
    """Test calendar functionality"""
    print("=" * 50)
    print("Testing Calendar Functionality")
    print("=" * 50)

    calendar = CalendarTools()

    # 1. Create events
    print("\n1. Creating calendar events...")
    now = datetime.now()
    tomorrow = now + timedelta(days=1)

    event1 = calendar.create_event(
        title="Team Weekly Meeting",
        start_time=tomorrow.replace(hour=10, minute=0).isoformat(),
        end_time=tomorrow.replace(hour=11, minute=0).isoformat(),
        description="Discuss project progress",
        location="Conference Room A",
        attendees=["john@example.com", "jane@example.com"],
        reminder_minutes=15,
    )
    print(f"   Created event: {event1['title']}")
    print(f"      Time: {event1['start_time']}")

    event2 = calendar.create_event(
        title="Lunch Appointment",
        start_time=tomorrow.replace(hour=12, minute=0).isoformat(),
        end_time=tomorrow.replace(hour=13, minute=0).isoformat(),
        location="Restaurant nearby",
    )
    print(f"   Created event: {event2['title']}")

    event3 = calendar.create_event(
        title="Project Deadline",
        start_time=(now + timedelta(days=7)).replace(hour=18, minute=0).isoformat(),
        is_all_day=True,
    )
    print(f"   Created event: {event3['title']}")

    # 2. List all events
    print("\n2. Listing all events...")
    all_events = calendar.list_events()
    print(f"   Total events: {len(all_events)}")
    for event in all_events:
        print(f"      - {event['title']} ({event['start_time']})")

    # 3. Get today's events
    print("\n3. Getting today's events...")
    today_events = calendar.get_events_today()
    print(f"   Events today: {len(today_events)}")

    # 4. Get upcoming events
    print("\n4. Getting upcoming events (24h)...")
    upcoming = calendar.get_upcoming_events(hours=24)
    print(f"   Events in next 24h: {len(upcoming)}")
    for event in upcoming:
        print(f"      - {event['title']}")

    # 5. Update event
    print("\n5. Updating event...")
    updated = calendar.update_event(event1["id"], location="Conference Room B")
    print(f"   Updated location: {updated['location']}")

    # 6. List calendars
    print("\n6. Listing all calendars...")
    calendars = calendar.list_calendars()
    for cal in calendars:
        print(f"      - {cal['name']}: {cal['event_count']} events")

    # 7. Cancel event
    print("\n7. Cancelling event...")
    cancelled = calendar.cancel_event(event2["id"])
    print(f"   Event '{cancelled['title']}' status: {cancelled['status']}")

    # 8. Delete event
    print("\n8. Deleting event...")
    calendar.delete_event(event3["id"])
    remaining = calendar.list_events()
    print(f"   Remaining events: {len(remaining)}")

    print("\n✓ Calendar functionality test passed!\n")


def test_system_settings():
    """Test system settings functionality"""
    print("=" * 50)
    print("Testing System Settings Functionality")
    print("=" * 50)

    executor = create_system_settings_executor()
    state = SystemSettingsState()

    # Helper to execute tool calls
    def call_tool(name, args=None):
        from agent_sim.core import ToolCall

        result = executor.execute(state, ToolCall(tool_name=name, arguments=args or {}))
        if not result.success:
            raise Exception(f"Tool {name} failed: {result.error}")
        return result.result

    # 1. Get all settings
    print("\n1. Getting all settings...")
    all_settings = call_tool("get_all_settings")
    print(f"   WiFi: {'ON' if all_settings['wifi_enabled'] else 'OFF'}")
    print(f"   Bluetooth: {'ON' if all_settings['bluetooth_enabled'] else 'OFF'}")
    print(f"   Volume: {all_settings['media_volume']}")

    # 2. Toggle WiFi
    print("\n2. Toggling WiFi...")
    wifi_state = call_tool("toggle_wifi", {"enabled": False})
    print(f"   WiFi is now: {'ON' if wifi_state['wifi_enabled'] else 'OFF'}")

    # 3. Set volume
    print("\n3. Setting volume...")
    volume = call_tool("set_volume", {"volume_type": "media", "level": 75})
    print(f"   Media volume set to: {volume['level']}")

    # 4. Toggle airplane mode
    print("\n4. Toggling airplane mode...")
    airplane = call_tool("toggle_airplane_mode", {"enabled": True})
    print(f"   Airplane mode: {'ON' if airplane['airplane_mode'] else 'OFF'}")

    # 5. Toggle dark mode
    print("\n5. Toggling dark mode...")
    dark_mode = call_tool("toggle_dark_mode", {"enabled": True})
    print(f"   Dark mode: {'ON' if dark_mode['dark_mode'] else 'OFF'}")

    print("\n✓ System settings functionality test passed!\n")


def test_photo_gallery():
    """Test photo gallery functionality"""
    print("=" * 50)
    print("Testing Photo Gallery Functionality")
    print("=" * 50)

    executor = create_photo_gallery_executor()
    state = PhotoGalleryState()

    # Helper to execute tool calls
    def call_tool(name, args=None):
        from agent_sim.core import ToolCall

        result = executor.execute(state, ToolCall(tool_name=name, arguments=args or {}))
        if not result.success:
            raise Exception(f"Tool {name} failed: {result.error}")
        return result.result

    # 1. List photos
    print("\n1. Listing photos...")
    photos = call_tool("list_photos", {"limit": 5})
    print(f"   Total photos: {len(photos)}")
    for photo in photos[:3]:
        print(f"      - {photo['filename']} ({photo['taken_date']})")

    # 2. Search photos
    print("\n2. Searching photos...")
    results = call_tool("search_photos", {"query": "beach"})
    print(f"   Found {len(results)} photo(s) matching 'beach'")

    # 3. Create album
    print("\n3. Creating album...")
    album = call_tool("create_album", {"name": "Vacation 2024"})["album"]
    print(f"   Created album: {album['name']}")

    # 4. Add to album
    print("\n4. Adding photos to album...")
    if photos:
        call_tool("add_to_album", {"album_id": album["id"], "photo_id": photos[0]["id"]})
        print("   Added 1 photo to album")

    # 5. Get favorites
    print("\n5. Getting favorite photos...")
    favorites = call_tool("get_favorites")
    print(f"   Favorite photos: {len(favorites)}")

    # 6. Get stats
    print("\n6. Getting gallery statistics...")
    stats = call_tool("get_stats")
    print(f"   Total photos: {stats['total_photos']}")
    print(f"   Total albums: {stats['total_albums']}")

    print("\n✓ Photo gallery functionality test passed!\n")


def test_browser():
    """Test browser functionality"""
    print("=" * 50)
    print("Testing Browser Functionality")
    print("=" * 50)

    executor = create_browser_executor()
    state = BrowserState()

    # Helper to execute tool calls
    def call_tool(name, args=None):
        from agent_sim.core import ToolCall

        result = executor.execute(state, ToolCall(tool_name=name, arguments=args or {}))
        if not result.success:
            raise Exception(f"Tool {name} failed: {result.error}")
        return result.result

    # 1. Navigate to URL
    print("\n1. Navigating to URLs...")
    navigation = call_tool("navigate_to", {"url": "https://www.example.com"})
    print(f"   Loaded: {navigation['current_url']}")

    tab2 = call_tool("new_tab", {"url": "https://www.github.com"})["tab"]
    print(f"   Loaded: {tab2['url']}")

    # 2. List tabs
    print("\n2. Listing tabs...")
    tabs = call_tool("list_tabs")
    print(f"   Open tabs: {len(tabs)}")
    for tab in tabs:
        print(f"      - [{tab['id']}] {tab['title']}")

    # 3. Add bookmark
    print("\n3. Adding bookmark...")
    bookmark = call_tool(
        "add_bookmark", {"title": "Example Site", "url": "https://www.example.com"}
    )["bookmark"]
    print(f"   Bookmarked: {bookmark['title']}")

    # 4. List bookmarks
    print("\n4. Listing bookmarks...")
    bookmarks = call_tool("list_bookmarks")
    print(f"   Total bookmarks: {len(bookmarks)}")
    for bm in bookmarks:
        print(f"      - {bm['title']}")

    # 5. Get history
    print("\n5. Getting browsing history...")
    history = call_tool("get_history", {"limit": 5})
    print(f"   Recent history: {len(history)} entries")
    for entry in history:
        print(f"      - {entry['url']}")

    # 6. Close tab
    print("\n6. Closing tab...")
    call_tool("close_tab", {"tab_id": tab2["id"]})
    remaining = call_tool("list_tabs")
    print(f"   Remaining tabs: {len(remaining)}")

    # 7. Get stats
    print("\n7. Getting browser statistics...")
    stats = call_tool("get_stats")
    print(f"   Open tabs: {stats['total_tabs']}")
    print(f"   Total bookmarks: {stats['total_bookmarks']}")

    print("\n✓ Browser functionality test passed!\n")


if __name__ == "__main__":
    try:
        print("\n" + "=" * 50)
        print("Start Testing Mobile Phone Task Subjects")
        print("=" * 50 + "\n")

        # Test all subjects
        test_contacts()
        test_sms()
        test_calendar()
        test_system_settings()
        test_photo_gallery()
        test_browser()

        print("=" * 50)
        print("✓ All tests passed!")
        print("=" * 50)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        raise SystemExit(1) from e
