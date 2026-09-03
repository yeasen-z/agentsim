"""AgentSim-native implementations of the AgentDojo suite tools."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Callable


def _items(container: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return container.get(key, [])


def _next_id(values: dict[str, Any]) -> str:
    return str(max((int(key) for key in values), default=0) + 1)


def _now() -> str:
    return datetime.now().isoformat()


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace(" ", "T"))


def _iso_datetime(value: str | datetime) -> str:
    parsed = value if isinstance(value, datetime) else _parse_datetime(value)
    return parsed.isoformat()


def _date_of(value: str) -> str:
    return _parse_datetime(value).date().isoformat()


def _sync_inbox(inbox: dict[str, Any]) -> None:
    emails = list(inbox["emails"].values())
    inbox["received"] = [deepcopy(email) for email in emails if email["status"] == "received"]
    inbox["sent"] = [deepcopy(email) for email in emails if email["status"] == "sent"]
    inbox["drafts"] = [deepcopy(email) for email in emails if email["status"] == "draft"]


def _send_email(
    inbox: dict[str, Any],
    recipients: list[str],
    subject: str,
    body: str,
    attachments: list[Any] | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> dict[str, Any]:
    parsed_attachments = []
    for attachment in attachments or []:
        if not isinstance(attachment, dict):
            raise ValueError("Attachments must be dictionaries.")
        if "type" not in attachment and "file_id" not in attachment:
            raise ValueError("Attachment must have a 'type' field.")
        if attachment.get("type") == "file" or "file_id" in attachment:
            if "file_id" not in attachment:
                raise ValueError("Attachment of type 'file' must have a 'file_id' field.")
            parsed_attachments.append(str(attachment["file_id"]))
        else:
            if "event_details" not in attachment:
                raise ValueError("Attachment of type 'event' must have an 'event_details' field.")
            parsed_attachments.append(deepcopy(attachment["event_details"]))

    email_id = _next_id(inbox["emails"])
    email = {
        "id_": email_id,
        "sender": inbox["account_email"],
        "recipients": list(recipients),
        "cc": list(cc or []),
        "bcc": list(bcc or []),
        "subject": subject,
        "body": body,
        "status": "sent",
        "read": True,
        "timestamp": _now(),
        "attachments": parsed_attachments,
    }
    inbox["emails"][email_id] = email
    _sync_inbox(inbox)
    return deepcopy(email)


def _email_tools(name: str, state: dict[str, Any], args: dict[str, Any]) -> Any:
    inbox = state["inbox"]
    emails = inbox["emails"]
    if name == "send_email":
        return _send_email(
            inbox,
            args["recipients"],
            args["subject"],
            args["body"],
            args.get("attachments"),
            args.get("cc"),
            args.get("bcc"),
        )
    if name == "delete_email":
        email_id = str(args["email_id"])
        if email_id not in emails:
            raise ValueError(f"Email with ID '{email_id}' not found.")
        inbox["trash"][email_id] = emails.pop(email_id)
        _sync_inbox(inbox)
        return f"Email with id {email_id} deleted successfully."
    if name == "get_unread_emails":
        unread = [email for email in emails.values() if not email["read"]]
        for email in unread:
            email["read"] = True
        _sync_inbox(inbox)
        return deepcopy(unread)
    if name == "get_sent_emails":
        return deepcopy([email for email in emails.values() if email["status"] == "sent"])
    if name == "get_received_emails":
        return deepcopy([email for email in emails.values() if email["status"] == "received"])
    if name == "get_draft_emails":
        return deepcopy([email for email in emails.values() if email["status"] == "draft"])
    if name == "search_emails":
        query = args["query"].lower()
        sender = args.get("sender")
        matches = [
            email
            for email in emails.values()
            if (sender is None or email["sender"].lower() == sender.lower())
            and (query in email["subject"].lower() or query in email["body"].lower())
        ]
        if not matches:
            raise ValueError("No emails found. Try with a different query.")
        return deepcopy(matches)
    if name in {"search_contacts_by_name", "search_contacts_by_email"}:
        query = args["query"].lower()
        field = "name" if name.endswith("by_name") else "email"
        matches = [contact for contact in inbox["contact_list"] if query in contact[field].lower()]
        if not matches:
            label = "name" if field == "name" else "email"
            raise ValueError(f"Contact with {label} '{args['query']}' not found.")
        return deepcopy(matches)
    raise KeyError(name)


def _events_on_day(calendar: dict[str, Any], day: str) -> list[dict[str, Any]]:
    return [event for event in calendar["events"].values() if _date_of(event["start_time"]) == day]


def _calendar_tools(name: str, state: dict[str, Any], args: dict[str, Any]) -> Any:
    calendar = state["calendar"]
    inbox = state["inbox"]
    events = calendar["events"]
    if name == "get_current_day":
        return calendar["current_day"]
    if name == "get_day_calendar_events":
        return deepcopy(_events_on_day(calendar, args["day"]))
    if name == "search_calendar_events":
        query = args["query"].lower()
        candidates = (
            _events_on_day(calendar, args["date"])
            if args.get("date") is not None
            else list(events.values())
        )
        matches = [
            event
            for event in candidates
            if query in event["title"].lower() or query in event["description"].lower()
        ]
        if not matches:
            raise ValueError("No events found. Try with a different query.")
        return deepcopy(matches)
    if name == "create_calendar_event":
        event_id = _next_id(events)
        email_recipients = [*(args.get("participants") or []), calendar["account_email"]]
        participants = list(set(email_recipients))
        event = {
            "id_": event_id,
            "title": args["title"],
            "description": args.get("description", ""),
            "start_time": _iso_datetime(args["start_time"]),
            "end_time": _iso_datetime(args["end_time"]),
            "location": args.get("location"),
            "participants": participants,
            "all_day": False,
            "status": "confirmed",
        }
        events[event_id] = event
        _send_email(
            inbox,
            email_recipients,
            f"Invitation: {event['title']}",
            event["description"],
            [{"type": "event", "event_details": deepcopy(event)}],
        )
        return deepcopy(event)
    if name == "cancel_calendar_event":
        event_id = str(args["event_id"])
        if event_id not in events:
            raise ValueError(f"Event with ID '{event_id}' not found.")
        event = events[event_id]
        event["status"] = "canceled"
        _send_email(
            inbox,
            event["participants"],
            f"Canceled: '{event['title']}'",
            "The event has been canceled.",
            [{"type": "event", "event_details": deepcopy(event)}],
        )
        return f"Event with ID {event_id} has been canceled and participants have been notified."
    if name == "reschedule_calendar_event":
        event_id = str(args["event_id"])
        if event_id not in events:
            raise ValueError(f"Event with ID '{event_id}' not found.")
        event = events[event_id]
        old_start = _parse_datetime(event["start_time"])
        old_end = _parse_datetime(event["end_time"])
        new_start = _parse_datetime(args["new_start_time"])
        new_end = (
            _parse_datetime(args["new_end_time"])
            if args.get("new_end_time") is not None
            else new_start + (old_end - old_start)
        )
        event["start_time"] = new_start.isoformat()
        event["end_time"] = new_end.isoformat()
        body = (
            "The event has been rescheduled. It will start on  "
            f"{new_start.date().isoformat()} at {new_start.time().isoformat()} and end on "
            f"{new_end.date().isoformat()} at {new_end.time().isoformat()}."
        )
        _send_email(
            inbox,
            event["participants"],
            "Rescheduled: '{event.title}'",
            body,
            [{"type": "event", "event_details": deepcopy(event)}],
        )
        return deepcopy(event)
    if name == "add_calendar_event_participants":
        event_id = str(args["event_id"])
        if event_id not in events:
            raise ValueError(f"Event with ID '{event_id}' not found.")
        events[event_id]["participants"].extend(args["participants"])
        return deepcopy(events[event_id])
    raise KeyError(name)


def _drive_tools(name: str, state: dict[str, Any], args: dict[str, Any]) -> Any:
    drive = state["cloud_drive"]
    files = drive["files"]
    if name == "search_files_by_filename":
        query = args["filename"].lower()
        return deepcopy([item for item in files.values() if query in item["filename"].lower()])
    if name == "create_file":
        file_id = _next_id(files)
        content = args["content"]
        item = {
            "id_": file_id,
            "filename": args["filename"],
            "content": content,
            "owner": drive["account_email"],
            "last_modified": _now(),
            "shared_with": {},
            "size": len(content),
        }
        files[file_id] = item
        return deepcopy(item)
    if name == "delete_file":
        file_id = str(args["file_id"])
        if file_id not in files:
            raise ValueError(f"File with ID '{file_id}' not found.")
        return deepcopy(files.pop(file_id))
    if name == "get_file_by_id":
        file_id = str(args["file_id"])
        if file_id not in files:
            raise ValueError(f"File with ID '{file_id}' not found.")
        return deepcopy(files[file_id])
    if name == "list_files":
        return deepcopy(list(files.values()))
    if name == "share_file":
        file_id = str(args["file_id"])
        if file_id not in files:
            raise ValueError(f"File with ID '{file_id}' not found.")
        files[file_id]["shared_with"][args["email"]] = args["permission"]
        return deepcopy(files[file_id])
    if name == "append_to_file":
        file_id = str(args["file_id"])
        if file_id not in files:
            raise ValueError(f"File with ID '{file_id}' not found.")
        item = files[file_id]
        item["content"] += args["content"]
        item["size"] = len(item["content"])
        item["last_modified"] = _now()
        return deepcopy(item)
    if name == "search_files":
        query = args["query"].lower()
        matches = [item for item in files.values() if query in item["content"].lower()]
        if not matches:
            raise ValueError(
                f"No files found with the given query ('{args['query']}'). Try a different search term."
            )
        return deepcopy(matches)
    raise KeyError(name)


def _banking_tools(name: str, state: dict[str, Any], args: dict[str, Any]) -> Any:
    account = state["bank_account"]
    if name == "get_iban":
        return account["iban"]
    if name == "get_balance":
        return account["balance"]
    if name == "get_most_recent_transactions":
        return deepcopy(account["transactions"][-int(args.get("n", 100)) :])
    if name == "get_scheduled_transactions":
        return deepcopy(account["scheduled_transactions"])
    if name == "read_file":
        return state["filesystem"]["files"].get(args["file_path"], "")
    if name == "get_user_info":
        user = state["user_account"]
        return {key: user[key] for key in ("first_name", "last_name", "street", "city")}
    if name == "update_password":
        state["user_account"]["password"] = args["password"]
        return {"message": "Password updated."}
    if name == "update_user_info":
        user = state["user_account"]
        for key in ("first_name", "last_name", "street", "city"):
            if args.get(key):
                user[key] = args[key]
        return {key: user[key] for key in ("first_name", "last_name", "street", "city")}

    transaction_id = max(
        [item["id"] for item in account["transactions"] + account["scheduled_transactions"]],
        default=0,
    ) + 1
    if name == "send_money":
        if args["amount"] <= 0:
            raise ValueError("Transaction amount must be positive.")
        if account["balance"] < args["amount"]:
            raise ValueError("Insufficient balance for transaction.")
        transaction = {
            "id": transaction_id,
            "sender": account["iban"],
            "recipient": args["recipient"],
            "amount": args["amount"],
            "subject": args["subject"],
            "date": args["date"],
            "recurring": False,
        }
        account["balance"] -= args["amount"]
        account["transactions"].append(transaction)
        return {"message": f"Transaction to {args['recipient']} for {args['amount']} sent."}
    if name == "schedule_transaction":
        transaction = {
            "id": transaction_id,
            "sender": account["iban"],
            "recipient": args["recipient"],
            "amount": args["amount"],
            "subject": args["subject"],
            "date": args["date"],
            "recurring": args["recurring"],
        }
        account["scheduled_transactions"].append(transaction)
        return {"message": f"Transaction to {args['recipient']} for {args['amount']} scheduled."}
    if name == "update_scheduled_transaction":
        transaction = next(
            (item for item in account["scheduled_transactions"] if item["id"] == args["id"]),
            None,
        )
        if transaction is None:
            raise ValueError(f"Transaction with ID {args['id']} not found.")
        for key in ("recipient", "amount", "subject", "date", "recurring"):
            if args.get(key):
                transaction[key] = args[key]
        return {"message": f"Transaction with ID {args['id']} updated."}
    raise KeyError(name)


def _slack_tools(name: str, state: dict[str, Any], args: dict[str, Any]) -> Any:
    slack = state["slack"]
    if name == "get_channels":
        return list(slack["channels"])
    if name == "add_user_to_channel":
        if args["user"] not in slack["users"]:
            raise ValueError(f"User {args['user']} not found in the users list")
        if args["channel"] not in slack["channels"]:
            raise ValueError(f"Channel {args['channel']} not found in the channels list")
        slack["user_channels"][args["user"]].append(args["channel"])
        return None
    if name == "read_channel_messages":
        if args["channel"] not in slack["channels"]:
            raise ValueError("Channel does not exist!")
        return deepcopy(slack["channel_inbox"].get(args["channel"], []))
    if name == "read_inbox":
        if args["user"] not in slack["users"]:
            raise ValueError(f"User {args['user']} not found in the users list")
        return deepcopy(slack["user_inbox"].get(args["user"], []))
    if name == "send_direct_message":
        recipient = args["recipient"]
        if recipient not in slack["users"]:
            raise ValueError(f"Recipient {recipient} not found in the users list")
        slack["user_inbox"].setdefault(recipient, []).append(
            {"sender": "bot", "recipient": recipient, "body": args["body"]}
        )
        return None
    if name == "send_channel_message":
        channel = args["channel"]
        if channel not in slack["channels"]:
            raise ValueError(f"Channel {channel} not found in the channels list")
        slack["channel_inbox"].setdefault(channel, []).append(
            {"sender": "bot", "recipient": channel, "body": args["body"]}
        )
        return None
    if name == "get_users_in_channel":
        channel = args["channel"]
        if channel not in slack["channels"]:
            raise ValueError(f"Channel {channel} not found in the channels list")
        return [user for user, channels in slack["user_channels"].items() if channel in channels]
    if name == "invite_user_to_slack":
        user = args["user"]
        if user in slack["users"]:
            raise ValueError(f"User {user} already in the users list")
        slack["users"].append(user)
        slack["user_inbox"][user] = []
        slack["user_channels"][user] = []
        return None
    if name == "remove_user_from_slack":
        user = args["user"]
        if user not in slack["users"]:
            raise ValueError(f"User {user} not found in the users list")
        slack["users"].remove(user)
        del slack["user_inbox"][user]
        del slack["user_channels"][user]
        return None
    if name in {"get_webpage", "post_webpage"}:
        web = state["web"]
        url = args["url"].removeprefix("https://").removeprefix("http://")
        web["web_requests"].append(url)
        if name == "post_webpage":
            web["web_content"][url] = args["content"]
            return None
        return web["web_content"].get(url, "404 Not Found")
    raise KeyError(name)


def _select(values: list[dict[str, Any]], field: str, accepted: list[str]) -> list[dict[str, Any]]:
    return [value for value in values if value[field] in accepted]


def _travel_tools(name: str, state: dict[str, Any], args: dict[str, Any]) -> Any:
    if name == "get_user_information":
        user = state["user"]
        return {
            "First Name": user["first_name"],
            "Last Name": user["last_name"],
            "ID Number": user["ID_number"],
            "Email": user["email"],
            "Phone Number": user["phone_number"],
            "Address": user["address"],
            "Passport Number": user["passport_number"],
            "Bank Account Number": user["bank_account_number"],
            "Credit Card Number": user["credit_card_number"],
        }

    hotels = state["hotels"]["hotel_list"]
    if name == "get_all_hotels_in_city":
        names = [hotel["name"] for hotel in hotels if hotel["city"] == args["city"]]
        return "Hotel Names: " + "\n".join(names) + "\n"
    if name == "get_hotels_prices":
        return {
            hotel["name"]: f"Price range: {hotel['price_min']} - {hotel['price_max']}"
            for hotel in _select(hotels, "name", args["hotel_names"])
        }
    if name == "get_rating_reviews_for_hotels":
        return {
            hotel["name"]: f"Rating: {hotel['rating']}\nReviews: " + "\n".join(hotel["reviews"])
            for hotel in _select(hotels, "name", args["hotel_names"])
        }
    if name == "get_hotels_address":
        return {
            hotel["name"]: hotel["address"]
            for hotel in hotels
            if hotel["name"] == args["hotel_name"]
        }

    restaurants = state["restaurants"]["restaurant_list"]
    if name == "get_all_restaurants_in_city":
        names = [item["name"] for item in restaurants if item["city"] == args["city"]]
        return f"Restaurant in {args['city']}: " + "\n".join(names) + "\n"
    restaurant_fields = {
        "get_cuisine_type_for_restaurants": "cuisine_type",
        "get_restaurants_address": "address",
        "get_contact_information_for_restaurants": "contact_information",
        "get_price_for_restaurants": "price_per_person",
        "check_restaurant_opening_hours": "operating_hours",
        "get_dietary_restrictions_for_all_restaurants": "dietary_restrictions",
    }
    if name in restaurant_fields:
        accepted = args["restaurant_names"]
        if name == "get_dietary_restrictions_for_all_restaurants":
            accepted_text = ", ".join(accepted)
            selected = [item for item in restaurants if item["name"] in accepted_text]
        else:
            selected = _select(restaurants, "name", accepted)
        field = restaurant_fields[name]
        return {item["name"]: item[field] for item in selected}
    if name == "get_rating_reviews_for_restaurants":
        return {
            item["name"]: f"Rating: {item['rating']}\nReviews: " + "\n".join(item["reviews"])
            for item in _select(restaurants, "name", args["restaurant_names"])
        }

    companies = state["car_rental"]["company_list"]
    if name == "get_all_car_rental_companies_in_city":
        names = [item["name"] for item in companies if item["city"] == args["city"]]
        return f"Car Rental Companies in {args['city']}: " + "\n".join(names) + "\n"
    company_fields = {
        "get_car_types_available": "car_types_available",
        "get_car_fuel_options": "fuel_options",
        "get_car_rental_address": "address",
        "get_car_price_per_day": "price_per_day",
    }
    if name in company_fields:
        selected = _select(companies, "name", args["company_name"])
        field = company_fields[name]
        return {item["name"]: item[field] for item in selected}
    if name == "get_rating_reviews_for_car_rental":
        return {
            item["name"]: f"Rating: {item['rating']}\nReviews: " + "\n".join(item["reviews"])
            for item in _select(companies, "name", args["company_name"])
        }

    if name in {"reserve_hotel", "reserve_restaurant", "reserve_car_rental"}:
        reservation = state["reservation"]
        reservation["contact_information"] = state["user"]["phone_number"]
        if name == "reserve_hotel":
            reservation.update(
                {
                    "reservation_type": "hotel",
                    "title": args["hotel"],
                    "start_time": _iso_datetime(args["start_day"]),
                    "end_time": _iso_datetime(args["end_day"]),
                }
            )
            return (
                f"Reservation for {args['hotel']} from {args['start_day']} to "
                f"{args['end_day']} has been made successfully."
            )
        if name == "reserve_restaurant":
            start = _parse_datetime(args["start_time"])
            end = start + timedelta(hours=2)
            reservation.update(
                {
                    "reservation_type": "restaurant",
                    "title": args["restaurant"],
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                }
            )
            return (
                f"Reservation for {args['restaurant']} from {start.strftime('%H:%M')} "
                f"to {end.strftime('%H:%M')} on {start.date().isoformat()} has been made successfully."
            )
        start = _parse_datetime(args["start_time"])
        reservation.update(
            {
                "reservation_type": "car",
                "title": args["company"],
                "start_time": start.isoformat(),
                "end_time": start.isoformat(),
            }
        )
        return (
            f"Reservation for a car at {args['company']} from {args['start_time']} "
            f"to {args.get('end_time')} has been made successfully."
        )
    if name == "get_flight_information":
        lines = []
        for flight in state["flights"]["flight_list"]:
            if (
                flight["departure_city"] == args["departure_city"]
                and flight["arrival_city"] == args["arrival_city"]
            ):
                departure = str(_parse_datetime(flight["departure_time"]))
                arrival = str(_parse_datetime(flight["arrival_time"]))
                lines.append(
                    f"Airline: {flight['airline']}, Flight Number: {flight['flight_number']}, "
                    f"Departure Time: {departure}, Arrival Time: {arrival}, Price: {flight['price']}, "
                    f"Contact Information: {flight['contact_information']}"
                )
        return "\n".join(lines)
    raise KeyError(name)


EMAIL_TOOLS = {
    "send_email",
    "delete_email",
    "get_unread_emails",
    "get_sent_emails",
    "get_received_emails",
    "get_draft_emails",
    "search_emails",
    "search_contacts_by_name",
    "search_contacts_by_email",
}
CALENDAR_TOOLS = {
    "get_current_day",
    "search_calendar_events",
    "get_day_calendar_events",
    "create_calendar_event",
    "cancel_calendar_event",
    "reschedule_calendar_event",
    "add_calendar_event_participants",
}
DRIVE_TOOLS = {
    "append_to_file",
    "search_files_by_filename",
    "create_file",
    "delete_file",
    "get_file_by_id",
    "list_files",
    "share_file",
    "search_files",
}


def execute_tool(suite: str, name: str, state: dict[str, Any], arguments: dict[str, Any]) -> Any:
    """Execute one benchmark tool against JSON-native authoritative state."""
    dispatchers: dict[str, Callable[[str, dict[str, Any], dict[str, Any]], Any]] = {
        "banking": _banking_tools,
        "slack": _slack_tools,
    }
    if suite in dispatchers:
        return dispatchers[suite](name, state, arguments)
    if name in EMAIL_TOOLS:
        return _email_tools(name, state, arguments)
    if name in CALENDAR_TOOLS:
        return _calendar_tools(name, state, arguments)
    if name in DRIVE_TOOLS:
        return _drive_tools(name, state, arguments)
    if suite == "travel":
        return _travel_tools(name, state, arguments)
    raise ValueError(f"Unknown AgentDojo tool {suite}.{name}")
