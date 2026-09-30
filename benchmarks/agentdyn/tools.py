"""AgentSim-native implementations of AgentDyn's shared application tools."""

from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime
from typing import Any, Callable

from benchmarks.common.clock import simulation_timestamp


def _next_id(values: dict[str, Any]) -> str:
    return str(max((int(key) for key in values), default=0) + 1)


def _now() -> str:
    return simulation_timestamp()


def _inbox(database: dict[str, Any], address: str | None = None) -> dict[str, Any]:
    email = address or database.get("current_account")
    if email is None:
        raise ValueError("No email account is login.")
    for inbox in database["inbox_list"]:
        if inbox["account_email"] == email:
            return inbox
    created = {
        "account_email": email,
        "initial_emails": [],
        "emails": {},
        "contact_list": [],
        "trash": {},
        "received": [],
        "sent": [],
        "drafts": [],
    }
    database["inbox_list"].append(created)
    return created


def _sync_inbox(inbox: dict[str, Any]) -> None:
    values = list(inbox["emails"].values())
    inbox["received"] = [deepcopy(item) for item in values if item["status"] == "received"]
    inbox["sent"] = [deepcopy(item) for item in values if item["status"] == "sent"]
    inbox["drafts"] = [deepcopy(item) for item in values if item["status"] == "draft"]


def _file_node(state: dict[str, Any], path: str) -> dict[str, Any]:
    current = state["filesystem"]["root"]
    for part in [item for item in path.strip("/").split("/") if item]:
        if current.get("type") != "directory" or part not in current["children"]:
            raise FileNotFoundError(f"Path {path} not found")
        current = current["children"][part]
    return current


def _parent_node(state: dict[str, Any], path: str) -> tuple[dict[str, Any], str]:
    parts = [item for item in path.strip("/").split("/") if item]
    if not parts:
        raise ValueError("Root has no parent")
    parent_path = "/".join(parts[:-1])
    parent = _file_node(state, parent_path) if parent_path else state["filesystem"]["root"]
    if parent.get("type") != "directory":
        raise ValueError(f"Parent directory for {path} not found")
    return parent, parts[-1]


def _add_node(state: dict[str, Any], path: str, node: dict[str, Any]) -> str:
    parent, name = _parent_node(state, path)
    if name in parent["children"]:
        suffix = 1
        while f"{name}({suffix})" in parent["children"] and suffix < 100:
            suffix += 1
        name = f"{name}({suffix})"
    parent["children"][name] = deepcopy(node)
    directory = "/".join(path.strip("/").split("/")[:-1])
    return f"{name} has been added to {directory}."


def _upload_file(state: dict[str, Any], path: str) -> str:
    node = deepcopy(_file_node(state, path))
    if node.get("type") != "file":
        raise IsADirectoryError(path)
    node["source_name"] = path.rstrip("/").rsplit("/", 1)[-1]
    file_id = _next_id(state["web_database"]["file_list"])
    state["web_database"]["file_list"][file_id] = node
    return file_id


def _parse_attachments(
    state: dict[str, Any], attachments: list[dict[str, Any]] | None
) -> list[Any]:
    parsed: list[Any] = []
    for attachment in attachments or []:
        if not isinstance(attachment, dict):
            raise ValueError("Attachments must be dictionaries.")
        if "type" not in attachment and "file_id" not in attachment:
            raise ValueError("Attachment must have a 'type' field.")
        if attachment.get("type") == "file" or "file_path" in attachment or "file_id" in attachment:
            if "file_path" in attachment:
                parsed.append(_upload_file(state, attachment["file_path"]))
            elif "file_id" in attachment:
                parsed.append(str(attachment["file_id"]))
            else:
                raise ValueError("Attachment of type 'file' requires file_path or file_id.")
        elif "event_details" in attachment:
            parsed.append(deepcopy(attachment["event_details"]))
        else:
            raise ValueError("Attachment of type 'event' requires event_details.")
    return parsed


def send_receive_email(
    state: dict[str, Any],
    sender: str,
    subject: str,
    body: str,
    recipients: list[str] | str,
    attachments: list[dict[str, Any]] | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    reservation: str | None = None,
    time: str | None = None,
    size: str | None = None,
) -> dict[str, Any]:
    database = state["email_database"]
    if reservation is not None:
        if time is None or size is None:
            raise ValueError("Reservation emails require both time and party size.")
        body = body.replace("@@@time@@@", str(time)).replace("@@@size@@@", str(size))
    recipients = [recipients] if isinstance(recipients, str) else list(recipients)
    parsed_attachments = _parse_attachments(state, attachments)
    sender_inbox = _inbox(database, sender)
    sent_id = _next_id(sender_inbox["emails"])
    sent = {
        "id_": sent_id,
        "sender": sender,
        "recipients": recipients,
        "cc": list(cc or []),
        "bcc": list(bcc or []),
        "subject": subject,
        "body": body,
        "status": "sent",
        "read": True,
        "timestamp": _now(),
        "attachments": parsed_attachments,
    }
    sender_inbox["emails"][sent_id] = sent
    _sync_inbox(sender_inbox)
    result = sent
    for recipient in recipients:
        recipient_inbox = _inbox(database, recipient)
        received_id = _next_id(recipient_inbox["emails"])
        result = {
            **deepcopy(sent),
            "id_": received_id,
            "recipients": [recipient],
            "status": "received",
            "read": False,
        }
        recipient_inbox["emails"][received_id] = result
        _sync_inbox(recipient_inbox)
    return deepcopy(result)


def _send_only_email(
    state: dict[str, Any],
    sender: str,
    subject: str,
    body: str,
    recipients: list[str],
    attachments: list[Any] | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
) -> dict[str, Any]:
    """Append a sent message without delivering a second copy to the sender."""
    inbox = _inbox(state["email_database"], sender)
    email_id = _next_id(inbox["emails"])
    message = {
        "id_": email_id,
        "sender": sender,
        "recipients": list(recipients),
        "cc": list(cc or []),
        "bcc": list(bcc or []),
        "subject": subject,
        "body": body,
        "status": "sent",
        "read": True,
        "timestamp": _now(),
        "attachments": deepcopy(attachments or []),
    }
    inbox["emails"][email_id] = message
    _sync_inbox(inbox)
    return deepcopy(message)


def _email_tool(name: str, state: dict[str, Any], args: dict[str, Any]) -> Any:
    database = state["email_database"]
    inbox = _inbox(database)
    if name == "send_email":
        send_receive_email(
            state,
            database["current_account"],
            args["subject"],
            args["body"],
            args["recipients"],
            args.get("attachments"),
            args.get("cc"),
            args.get("bcc"),
        )
        return "The email has been sent successfully."
    if name == "get_unread_emails":
        unread = [item for item in inbox["emails"].values() if not item["read"]]
        for item in unread:
            item["read"] = True
        _sync_inbox(inbox)
        return deepcopy(unread)
    if name == "get_received_emails":
        return deepcopy(inbox["received"])
    if name == "get_sent_emails":
        return deepcopy(inbox["sent"])
    if name == "search_emails":
        query = args["query"].casefold()
        sender = args.get("sender")
        result = [
            deepcopy(item)
            for item in inbox["emails"].values()
            if (sender is None or item["sender"].casefold() == sender.casefold())
            and (query in item["subject"].casefold() or query in item["body"].casefold())
        ]
        if not result:
            raise ValueError("No emails found. Try with a different query.")
        return result
    if name == "delete_email":
        email_id = str(args["email_id"])
        if email_id not in inbox["emails"]:
            raise ValueError(f"Email with ID '{email_id}' not found.")
        inbox["trash"][email_id] = inbox["emails"].pop(email_id)
        _sync_inbox(inbox)
        return f"Email with id {email_id} deleted successfully."
    raise KeyError(name)


def _filesystem_tool(name: str, state: dict[str, Any], args: dict[str, Any]) -> Any:
    if name == "list_directory":
        node = _file_node(state, args["path"])
        if node.get("type") != "directory":
            return f"{args['path']} is not a directory."
        if not node.get("permissions", {}).get("read", True):
            raise PermissionError(f"Read permission denied for {args['path']}")
        # Upstream returns the metadata records as a string, not just names.
        return str(
            [
                {
                    "name": child_name,
                    "type": child.get("type", "file"),
                    # Upstream returns ``Permissions.dict()`` whose field
                    # order is model-declaration order, not YAML's sorted
                    # mapping order.
                    "permissions": {
                        key: child.get("permissions", {}).get(key, default)
                        for key, default in (
                            ("read", True),
                            ("write", child.get("type") == "directory"),
                            ("execute", False),
                        )
                    },
                }
                for child_name, child in node["children"].items()
            ]
        )
    if name == "read_file":
        node = _file_node(state, args["path"])
        if node.get("type") == "directory":
            raise IsADirectoryError(f"Path {args['path']} is a directory, not a file")
        if not node.get("permissions", {}).get("read", True):
            raise PermissionError(f"Read permission denied for {args['path']}")
        return node["content"]
    if name == "create_dir":
        current = state["filesystem"]["root"]
        for part in [item for item in args["path"].strip("/").split("/") if item]:
            if current.get("type") != "directory":
                raise ValueError(f"Cannot create directory: '{part}' is a file.")
            current = current["children"].setdefault(
                part,
                {
                    "type": "directory",
                    "children": {},
                    "permissions": {"read": True, "write": True, "execute": False},
                },
            )
        return f"Directory {args['path']} created."
    if name == "create_file":
        parent, filename = _parent_node(state, args["path"])
        parent["children"][filename] = {
            "type": "file",
            "content": str(args.get("content", "")),
            "permissions": {"read": True, "write": True, "execute": False},
        }
        return f"File {args['path']} created"
    if name == "delete_node":
        parent, filename = _parent_node(state, args["path"])
        if filename not in parent["children"]:
            raise FileNotFoundError(f"Path {args['path']} not found")
        del parent["children"][filename]
        return f"{args['path']} successfully deleted."
    if name in {"copy_node", "move_node"}:
        source_path = args["source_path"]
        destination_path = args["destination_path"]
        source = deepcopy(_file_node(state, source_path))
        source_name = source_path.rstrip("/").rsplit("/", 1)[-1]
        try:
            destination = _file_node(state, destination_path)
        except FileNotFoundError:
            destination = None
        if destination is not None:
            if destination.get("type") != "directory":
                raise FileExistsError(f"Destination '{destination_path}' already exists.")
            parent, target = destination, source_name
        else:
            parent, target = _parent_node(state, destination_path)
        if name == "copy_node" and target in parent["children"]:
            suffix = 1
            while f"{target}_{suffix}" in parent["children"]:
                suffix += 1
            target = f"{target}_{suffix}"
        parent["children"][target] = source
        if name == "move_node":
            source_parent, old_name = _parent_node(state, source_path)
            del source_parent["children"][old_name]
            return f"Successfully moved '{source_path}' to '{destination_path}'."
        return f"Successfully copied '{source_path}' to '{destination_path}' (as '{target}')."
    raise KeyError(name)


def _web_page(state: dict[str, Any], url: str) -> dict[str, Any]:
    standardized = re.sub(r"^https?://", "", url).rstrip("/")
    for page in state["web_database"]["web_list"]:
        if re.sub(r"^https?://", "", page["web_url"]).rstrip("/") == standardized:
            return page
    raise ValueError(f"Webpage {url!r} not found.")


def _download_id(state: dict[str, Any], file_id: str, save_dir: str) -> str:
    files = state["web_database"]["file_list"]
    if str(file_id) not in files:
        return "Source Not Found"
    source = files[str(file_id)]
    return _add_node(state, f"{save_dir}/{source['source_name']}", source)


def _web_tool(
    name: str,
    state: dict[str, Any],
    args: dict[str, Any],
    invoke_internal: Callable[[str, dict[str, Any]], Any],
) -> Any:
    if name == "download_file_through_id":
        return _download_id(state, str(args["file_id"]), args.get("save_dir", "/downloads"))
    if name == "download_file_through_url":
        page = _web_page(state, args["url"])
        source = page.get("download_source")
        if source is None:
            return "Source Not Found. Try to directly access the URL."
        return _download_id(state, str(source), args.get("save_dir", "/downloads"))
    try:
        page = _web_page(state, args["url"])
    except ValueError:
        if name == "browse_webpage":
            return "404 Not Found"
        raise
    if name == "browse_webpage":
        if not page["field_to_parameters"] and page["web_function"]:
            function = page["web_function"][0]
            return invoke_internal(function["handler"], deepcopy(function["static_parameters"]))
        return page["web_content"]
    if name == "input_to_webpage":
        if "inputs" in args:
            values = args["inputs"]
        else:
            values = dict(zip(args["input_ids"], args["input_values"], strict=True))
        mapped = {page["field_to_parameters"][key]: value for key, value in values.items()}
        if not page["web_function"]:
            return page["web_content"]
        function = page["web_function"][0]
        return invoke_internal(
            function["handler"],
            {**deepcopy(function["static_parameters"]), **mapped},
        )
    raise KeyError(name)


def _calendar_tool(name: str, state: dict[str, Any], args: dict[str, Any]) -> Any:
    calendar = state["calendar"]
    events = calendar["events"]
    if name == "get_current_day":
        return calendar["current_day"]
    if name == "get_day_calendar_events":
        return [
            deepcopy(event)
            for event in events.values()
            if event["start_time"].split("T", 1)[0] == args["day"]
        ]
    if name == "search_calendar_events":
        query = args["query"].casefold()
        result = [
            deepcopy(event)
            for event in events.values()
            if (args.get("date") is None or event["start_time"].split("T", 1)[0] == args["date"])
            and (query in event["title"].casefold() or query in event["description"].casefold())
        ]
        if not result:
            raise ValueError("No events found. Try with a different query.")
        return result
    if name == "create_calendar_event":
        event_id = _next_id(events)
        participants = list(args.get("participants") or [])
        participants.append(calendar["account_email"])
        participants = list(set(participants))
        event = {
            "id_": event_id,
            "title": args["title"],
            "description": args.get("description", ""),
            "start_time": datetime.strptime(args["start_time"], "%Y-%m-%d %H:%M").isoformat(),
            "end_time": datetime.strptime(args["end_time"], "%Y-%m-%d %H:%M").isoformat(),
            "location": args.get("location"),
            "participants": participants,
            "all_day": False,
            "status": "confirmed",
        }
        events[event_id] = event
        sender = state["email_database"]["current_account"]
        _send_only_email(
            state,
            sender,
            f"Invitation: {event['title']}",
            event["description"],
            participants,
            [deepcopy(event)],
        )
        return deepcopy(event)
    event_id = str(args["event_id"])
    if event_id not in events:
        raise ValueError(f"Event with ID '{event_id}' not found.")
    event = events[event_id]
    if name == "cancel_calendar_event":
        event["status"] = "canceled"
        _send_only_email(
            state,
            state["email_database"]["current_account"],
            f"Canceled: '{event['title']}'",
            "The event has been canceled.",
            event["participants"],
            [deepcopy(event)],
        )
        return f"Event with ID {event_id} has been canceled and participants have been notified."
    if name == "reschedule_calendar_event":
        old_start = datetime.fromisoformat(event["start_time"])
        old_end = datetime.fromisoformat(event["end_time"])
        new_start = datetime.strptime(args["new_start_time"], "%Y-%m-%d %H:%M")
        new_end = (
            datetime.strptime(args["new_end_time"], "%Y-%m-%d %H:%M")
            if args.get("new_end_time")
            else new_start + (old_end - old_start)
        )
        event["start_time"] = new_start.isoformat()
        event["end_time"] = new_end.isoformat()
        _send_only_email(
            state,
            state["email_database"]["current_account"],
            "Rescheduled: '{event.title}'",
            (
                "The event has been rescheduled. It will start on  "
                f"{new_start.date().isoformat()} at {new_start.time().isoformat()} and end on "
                f"{new_end.date().isoformat()} at {new_end.time().isoformat()}."
            ),
            event["participants"],
            [deepcopy(event)],
        )
        return deepcopy(event)
    if name == "add_calendar_event_participants":
        event["participants"].extend(args["participants"])
        return deepcopy(event)
    raise KeyError(name)


def _bank_account(database: dict[str, Any], iban: str | None = None) -> dict[str, Any] | None:
    target = iban or database["current_account"]
    return next((item for item in database["account_list"] if item["iban"] == target), None)


def _transfer(
    database: dict[str, Any],
    sender: dict[str, Any],
    recipient: str,
    amount: float,
    subject: str,
    date: str,
) -> str:
    if amount <= 0:
        return "The amount must be greater than 0."
    recipient_account = _bank_account(database, recipient)
    if recipient_account is None:
        return "Recipient bank account not found."
    if sender["balance"] < amount:
        return "Insufficient funds."
    transaction = {
        "id": max(
            [item["id"] for item in sender["transactions"]]
            + [item["id"] for item in sender.get("scheduled_transactions", [])],
            default=0,
        )
        + 1,
        "sender": sender["iban"],
        "recipient": recipient,
        "amount": amount,
        "subject": subject,
        "date": date,
        "recurring": False,
    }
    sender["balance"] -= amount
    sender["transactions"].append(transaction)
    recipient_account["balance"] += amount
    recipient_account["transactions"].append(deepcopy(transaction))
    # Upstream's tool signature validates ``amount`` as float before
    # interpolating the confirmation string (so 200 is rendered as 200.0).
    return f"Sent {float(amount)} to {recipient}."


def _daily_bank_tool(name: str, state: dict[str, Any], args: dict[str, Any]) -> Any:
    database = state["bank_database"]
    account = _bank_account(database)
    if account is None:
        return "Bank account not found."
    if name == "get_balance":
        return account["balance"]
    if name == "send_money":
        if args["amount"] > 500 and not account["verification"]:
            token = f"{len(account['verification_stack']) + 1:06d}"
            account["verification_stack"][token] = {"tool": name, "arguments": deepcopy(args)}
            send_receive_email(
                state,
                "banking_platform@mail.com",
                "Transaction Approval Request OTP",
                f"Here is a transaction approval request. Please use the following OTP to approve it: {token}",
                [state["email_database"]["current_account"]],
            )
            return (
                "Your transaction amount exceeds $500. Please verify your account to approve this "
                "transaction. An email including verification one-time password (OTP) has been sent "
                "to your inbox."
            )
        return _transfer(
            database,
            account,
            args["recipient"],
            args["amount"],
            args["subject"],
            args["date"],
        )
    if name == "verify_transaction":
        if args["otp"] not in account["verification_stack"]:
            return "One Time Password is incorrect, verification failed."
        pending = account["verification_stack"].pop(args["otp"])
        account["verification"] = True
        result = _daily_bank_tool(pending["tool"], state, pending["arguments"])
        account["verification"] = False
        return f"Account verified. {result}"
    raise KeyError(name)


EMAIL_TOOLS = {
    "send_email",
    "get_unread_emails",
    "get_received_emails",
    "get_sent_emails",
    "delete_email",
    "search_emails",
}
FILESYSTEM_TOOLS = {
    "list_directory",
    "create_file",
    "create_dir",
    "read_file",
    "delete_node",
    "copy_node",
    "move_node",
}
WEB_TOOLS = {
    "browse_webpage",
    "input_to_webpage",
    "download_file_through_url",
    "download_file_through_id",
}
CALENDAR_TOOLS = {
    "add_calendar_event_participants",
    "cancel_calendar_event",
    "create_calendar_event",
    "get_current_day",
    "get_day_calendar_events",
    "reschedule_calendar_event",
    "search_calendar_events",
}


def execute_shared(
    suite: str,
    name: str,
    state: dict[str, Any],
    args: dict[str, Any],
    invoke_internal: Callable[[str, dict[str, Any]], Any],
) -> Any:
    if name in EMAIL_TOOLS:
        return _email_tool(name, state, args)
    if name in FILESYSTEM_TOOLS:
        return _filesystem_tool(name, state, args)
    if name in WEB_TOOLS:
        return _web_tool(name, state, args, invoke_internal)
    if name in CALENDAR_TOOLS:
        return _calendar_tool(name, state, args)
    if suite == "dailylife" and name in {"send_money", "get_balance", "verify_transaction"}:
        return _daily_bank_tool(name, state, args)
    raise KeyError(name)


def execute_tool(suite: str, name: str, state: dict[str, Any], args: dict[str, Any]) -> Any:
    """Execute one public AgentDyn tool against JSON-native authoritative state."""
    from .github_tools import GITHUB_TOOLS, execute_github, execute_github_internal
    from .shopping_tools import SHOPPING_TOOLS, execute_shopping, execute_shopping_internal

    def invoke_internal(handler: str, parameters: dict[str, Any]) -> Any:
        if handler == "send_receive_email":
            return send_receive_email(
                state,
                parameters["sender"],
                parameters["subject"],
                parameters["body"],
                parameters["recipients"],
                parameters.get("attachments"),
                parameters.get("cc"),
                parameters.get("bcc"),
                parameters.get("reservation"),
                parameters.get("time"),
                parameters.get("size"),
            )
        if handler == "send_receive_email_with_login":
            if (
                parameters["username"] != parameters["username_groundtruth"]
                or parameters["password"] != parameters["password_groundtruth"]
            ):
                raise ValueError("Login failed. Invalid username or password.")
            result = send_receive_email(
                state,
                parameters["sender"],
                parameters["subject"],
                parameters["body"],
                parameters["recipients"],
                parameters.get("attachments"),
                parameters.get("cc"),
                parameters.get("bcc"),
            )
            return parameters.get("return_str", result)
        if handler == "download_file_through_id":
            return _download_id(
                state,
                str(parameters["file_id"]),
                parameters.get("save_dir", "/downloads"),
            )
        try:
            return execute_shopping_internal(handler, state, parameters)
        except KeyError:
            return execute_github_internal(handler, state, parameters)

    if suite == "shopping" and name in SHOPPING_TOOLS:
        return execute_shopping(name, state, args)
    if suite == "github" and name in GITHUB_TOOLS:
        return execute_github(name, state, args)
    shared_tools = EMAIL_TOOLS | FILESYSTEM_TOOLS | WEB_TOOLS | CALENDAR_TOOLS
    if name in shared_tools or (
        suite == "dailylife" and name in {"send_money", "get_balance", "verify_transaction"}
    ):
        return execute_shared(suite, name, state, args, invoke_internal)
    raise ValueError(f"Unknown AgentDyn {suite} tool: {name}")


__all__ = [
    "CALENDAR_TOOLS",
    "EMAIL_TOOLS",
    "FILESYSTEM_TOOLS",
    "WEB_TOOLS",
    "_add_node",
    "_bank_account",
    "_daily_bank_tool",
    "_download_id",
    "_file_node",
    "_inbox",
    "_next_id",
    "_sync_inbox",
    "_transfer",
    "_upload_file",
    "execute_shared",
    "execute_tool",
    "send_receive_email",
]
