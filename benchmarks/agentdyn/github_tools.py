"""Native GitHub behavior for AgentDyn."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from .tools import _file_node, send_receive_email


def _account(
    platform: dict[str, Any], *, username: str | None = None, email: str | None = None
) -> dict[str, Any] | None:
    email = email if email is not None else (platform["current_account_email"] if username is None else None)
    return next(
        (
            item
            for item in platform["account_list"]
            if (username is not None and item["username"] == username)
            or (email is not None and item["email"] == email)
        ),
        None,
    )


def _directory() -> dict[str, Any]:
    return {
        "type": "directory",
        "children": {},
        "permissions": {"read": True, "write": True, "execute": False},
    }


def _send_otp(
    state: dict[str, Any],
    account: dict[str, Any],
    subject: str,
    body: str,
    tool: str,
    args: dict[str, Any],
) -> None:
    token = f"{len(account['verification_stack']) + 1:06d}"
    account["verification_stack"][token] = {"tool": tool, "arguments": deepcopy(args)}
    send_receive_email(
        state,
        "github-noreply@github.com",
        subject,
        body + token,
        [account["email"]],
    )


def _verify(state: dict[str, Any], account: dict[str, Any], otp: str) -> str:
    if not account["verification_stack"]:
        return "One Time Password is incorrect, verification failed."
    token = otp if otp in account["verification_stack"] else next(iter(account["verification_stack"]))
    pending = account["verification_stack"].pop(token)
    account["verification"] = True
    result = execute_github(pending["tool"], state, pending["arguments"])
    account["verification"] = False
    return f"Account verified. {result}"


def _tree(node: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for name, child in node["children"].items():
        if name == ".git_config":
            continue
        result[name] = (
            {"type": "directory", "children": _tree(child)}
            if child["type"] == "directory"
            else {"type": "file"}
        )
    return result


def _repo_root(state: dict[str, Any], local_path: str) -> tuple[dict[str, Any], str, list[str]]:
    parts = [part for part in local_path.strip("/").split("/") if part]
    nodes = [state["filesystem"]["root"]]
    current = nodes[0]
    for part in parts:
        if current.get("type") != "directory" or part not in current["children"]:
            raise FileNotFoundError(local_path)
        current = current["children"][part]
        nodes.append(current)
    for depth in range(len(nodes) - 1, -1, -1):
        node = nodes[depth]
        if node.get("type") == "directory" and ".git_config" in node["children"]:
            config = json.loads(node["children"][".git_config"]["content"])
            return node, config["repo_name"], parts[depth:]
    raise ValueError("Local path is not inside a cloned GitHub repository (no .git_config found).")


def _sync_to_remote(local: dict[str, Any], remote: dict[str, Any], force: bool) -> None:
    for name, child in local["children"].items():
        if name == ".git_config":
            continue
        if child["type"] == "file":
            if (
                not force
                and name in remote["children"]
                and remote["children"][name].get("type") == "file"
                and remote["children"][name]["content"] != child["content"]
            ):
                raise ValueError(f"Conflict detected in '{name}' during push.")
            remote["children"][name] = deepcopy(child)
        else:
            target = remote["children"].setdefault(name, _directory())
            _sync_to_remote(child, target, force)


def execute_github(name: str, state: dict[str, Any], args: dict[str, Any]) -> Any:
    platform = state["github_platform"]
    account = _account(platform)
    if name == "login_github_account":
        candidate = _account(platform, username=args["username"])
        if candidate is None:
            return "Username is incorrect."
        if candidate["password"] != args["password"]:
            return "Password is incorrect."
        platform["current_account_email"] = candidate["email"]
        return f"Login successful. You are now logged in as {candidate['username']}."
    if account is None:
        raise ValueError("Please login your github account first.")
    if name == "verify_github_account":
        return _verify(state, account, args["otp"])
    if name == "get_github_linked_unread_emails":
        inbox = next(
            item
            for item in state["email_database"]["inbox_list"]
            if item["account_email"] == account["email"]
        )
        result = [item for item in inbox["emails"].values() if not item["read"]]
        for item in result:
            item["read"] = True
        inbox["received"] = [
            deepcopy(item) for item in inbox["emails"].values() if item["status"] == "received"
        ]
        return deepcopy(result)
    if name == "get_logged_in_github_user_information":
        repositories = [f"{account['username']}/{item}" for item in account["repos"]]
        return {
            "email": account["email"],
            "username": account["username"],
            "password": account["password"],
            "repository": str(repositories),
            "starred repository": str(account["starred_repos"]),
        }
    if name == "get_github_account_user_information":
        if args.get("username") is None and args.get("email") is None:
            raise ValueError("You should provide at least one of: username or email.")
        target = _account(platform, username=args.get("username"), email=args.get("email"))
        if target is None:
            return {}
        repositories = [f"{target['username']}/{item}" for item in target["repos"]]
        return {
            "email": target["email"],
            "username": target["username"],
            "repository": str(repositories),
            "starred repository": str(target["starred_repos"]),
        }
    if name == "get_github_repository_information":
        if args["repo_name"] not in platform["repository_list"]:
            raise ValueError(f"Repository {args['repo_name']} not found.")
        repo = platform["repository_list"][args["repo_name"]]
        return {
            "name": repo["repo_name"],
            "owner": repo["owner"],
            "collaborators": str(repo["collaborators"]),
            "pending collaborators": str(repo["pending_collaborators"]),
            "stars": str(repo["stars"]),
            "repository file tree": str(_tree(repo["content"])),
            "issues": str(repo["issues"]),
        }
    verification_messages = {
        "update_github_account_password": (
            "Github Platform Password Updating OTP",
            "Your password updating OTP is: ",
            "You should verify your account first. An email including verification one-time password (OTP) has been sent to your inbox.",
        ),
        "git_create_repo": (
            "Github Platform Repository Deletion OTP",
            "Your github repository creation OTP is: ",
            "Please verify your account to proceed the repository creation. An email including verification one-time password (OTP) has been sent to your inbox.",
        ),
        "git_delete_repo": (
            "Github Platform Repository Deletion OTP",
            "Your github repository deletion OTP is: ",
            "Please verify your account to proceed the repository deletion action. An email including verification one-time password (OTP) has been sent to your inbox.",
        ),
        "git_transfer_repo_ownership": (
            "Github Repository Transfer OTP",
            "Your repository transfer OTP is: ",
            "Verification required. An email with an OTP has been sent to your inbox to confirm the transfer.",
        ),
        "git_invite_collaborators": (
            "Github Repository Invitation OTP",
            "Your repository Invitation OTP is: ",
            "Verification required. An email with an OTP has been sent to your inbox to confirm the invitation.",
        ),
        "git_get_linked_ssh_keys": (
            "Github Platform Request SSH Key OTP",
            "Your ssh key request OTP is: ",
            "You should verify your account first. An email including verification one-time password (OTP) has been sent to your inbox.",
        ),
        "git_add_ssh_key": (
            "Github Platform Add SSH Key OTP",
            "Your ssh key updating OTP is: ",
            "You should verify your account first. An email including verification one-time password (OTP) has been sent to your inbox.",
        ),
        "git_delete_ssh_key": (
            "Github Platform Remove SSH Key OTP",
            "Your ssh key updating OTP is: ",
            "You should verify your account first. An email including verification one-time password (OTP) has been sent to your inbox.",
        ),
    }
    if name in verification_messages and not account["verification"]:
        subject, body, message = verification_messages[name]
        _send_otp(state, account, subject, body, name, args)
        return message
    if name == "update_github_account_password":
        account["password"] = args["password"]
        return "Password updated."
    if name == "git_create_repo":
        full_name = f"{account['username']}/{args['repo_name']}"
        if full_name in platform["repository_list"]:
            return f"Repository '{full_name}' already exists."
        platform["repository_list"][full_name] = {
            "repo_name": args["repo_name"],
            "owner": account["username"],
            "collaborators": [],
            "pending_collaborators": [],
            "stars": [],
            "content": _directory(),
            "issues": [],
        }
        account["repos"].append(full_name)
        return f"The repository of '{full_name}' successfully created."
    if name == "git_delete_repo":
        repo_name = args["repo_name"]
        if repo_name not in platform["repository_list"]:
            return f"Repository '{repo_name}' not found."
        repo = platform["repository_list"][repo_name]
        if repo["owner"] != account["username"]:
            return f"Only the owner (@{repo['owner']}) can delete this repository."
        del platform["repository_list"][repo_name]
        short_name = repo_name.rsplit("/", 1)[-1]
        if short_name in account["repos"]:
            account["repos"].remove(short_name)
        return f"The repository of '{repo_name}' was successfully deleted."
    if name == "git_transfer_repo_ownership":
        repo_name = args["repo_name"]
        if repo_name not in platform["repository_list"]:
            return f"Repository '{repo_name}' not found."
        repo = platform["repository_list"][repo_name]
        target = _account(
            platform,
            username=args.get("new_owner_username"),
            email=args.get("new_owner_email"),
        )
        if target is None:
            raise ValueError("Invalid target account.")
        short_name = repo_name.rsplit("/", 1)[-1]
        new_name = f"{target['username']}/{short_name}"
        repo["owner"] = target["username"]
        platform["repository_list"][new_name] = repo
        del platform["repository_list"][repo_name]
        if short_name in account["repos"]:
            account["repos"].remove(short_name)
        target["repos"].append(short_name)
        return (
            f"Successfully transferred '{short_name}' to {target['username']}. "
            f"New repository path: {new_name}."
        )
    if name == "git_clone":
        repo_name = args["repo_name"]
        if repo_name not in platform["repository_list"]:
            return f"Repository '{repo_name}' not found on GitHub."
        target = _file_node(state, args.get("local_dir_path", "/"))
        if target["type"] != "directory":
            return f"Target path '{args.get('local_dir_path', '/')}' is invalid."
        short_name = repo_name.rsplit("/", 1)[-1]
        if short_name in target["children"]:
            return f"'{short_name}' already exists."
        clone = deepcopy(platform["repository_list"][repo_name]["content"])
        clone["children"][".git_config"] = {
            "type": "file",
            "content": json.dumps({"repo_name": repo_name}),
            "permissions": {"read": True, "write": False, "execute": False},
        }
        target["children"][short_name] = clone
        return f"Cloning '{repo_name}' into '{args.get('local_dir_path', '/')}/{short_name}'... done."
    if name == "git_invite_collaborators":
        repo_name = args["repo_name"]
        if repo_name not in platform["repository_list"]:
            return f"Repository '{repo_name}' not found."
        repo = platform["repository_list"][repo_name]
        collaborator = args["collaborator_email"]
        if collaborator in repo["collaborators"]:
            return f"{collaborator} is already a collaborator."
        link = f"https://www.github_receive_invitation.com/{repo_name}/{collaborator}/"
        state["web_database"]["web_list"].append(
            {
                "web_url": link,
                "web_content": "You have successfully accepted the invitation.",
                "field_to_parameters": {},
                "web_function": [
                    {
                        "handler": "git_invite_collaborators_wo_verification",
                        "static_parameters": {
                            "repo_name": repo_name,
                            "collaborator_email": collaborator,
                        },
                    }
                ],
                "download_source": None,
                "web_requests": [],
            }
        )
        letter_template = f"""
          Hello, 
          
          {repo['owner']} has invited you to collaborate on the GitHub repository {repo_name}.

          To accept this invitation, please click the link below:
          {link}

          If you were not expecting this invitation, you can safely ignore this email.

          Best regards,
          GitHub
        """
        send_receive_email(
            state,
            "github-noreply@github.com",
            f"Github Collaborator Invitation for Repository {repo_name}",
            letter_template,
            [collaborator],
        )
        repo["pending_collaborators"].append(collaborator)
        return f"An invitation link for the repository '{repo_name} has been sent to {collaborator}'. The collaborator will be added once they accept the email invitation."
    if name == "git_issue":
        repo_name = args["repo_name"]
        if repo_name not in platform["repository_list"]:
            return f"Repository '{repo_name}' not found."
        platform["repository_list"][repo_name]["issues"].append(
            {
                "owner_username": account["username"],
                "comments": [
                    {
                        "title": args["title"],
                        "body": args["comment_body"],
                        "timestamp": datetime_now(),
                    }
                ],
            }
        )
        return f"New issue successfully created in '{repo_name}'."
    if name == "git_push":
        try:
            root, repo_name, relative = _repo_root(state, args["local_path"])
        except (FileNotFoundError, ValueError) as error:
            return str(error)
        repo = platform["repository_list"].get(repo_name)
        if repo is None:
            return f"Remote repository '{repo_name}' not found."
        target = _file_node(state, args["local_path"])
        if not relative:
            _sync_to_remote(root, repo["content"], args.get("force", False))
        else:
            remote_parent = repo["content"]
            for part in relative[:-1]:
                remote_parent = remote_parent["children"].setdefault(part, _directory())
            if target["type"] == "file":
                remote_parent["children"][relative[-1]] = deepcopy(target)
            else:
                remote = remote_parent["children"].setdefault(relative[-1], _directory())
                _sync_to_remote(target, remote, args.get("force", False))
        return f"Successfully pushed '{args['local_path']}' to remote '{repo_name}'."
    if name == "git_pull":
        try:
            root, repo_name, _ = _repo_root(state, args.get("local_path", "/"))
        except (FileNotFoundError, ValueError):
            repo_name = args.get("repo_name")
            root = None
        if not repo_name:
            return "Could not find a .git_config file. Please navigate into a cloned repository."
        if root is None:
            return "Could not find a .git_config file. Please navigate into a cloned repository."
        remote = platform["repository_list"].get(repo_name)
        if remote is None:
            return f"Remote repository '{repo_name}' not found."
        for child_name, child in remote["content"]["children"].items():
            root["children"][child_name] = deepcopy(child)
        return f"Successfully pulled updates from '{repo_name}' into local repository root."
    if name in {"git_star", "git_unstar"}:
        repo_name = args["repo_name"]
        if repo_name not in platform["repository_list"]:
            return f"Repository '{repo_name}' not found."
        repo = platform["repository_list"][repo_name]
        if name == "git_star":
            if account["email"] in repo["stars"]:
                return f"You have already starred '{repo_name}'."
            repo["stars"].append(account["email"])
            account["starred_repos"].append(repo_name)
            return f"Successfully starred '{repo_name}'."
        if account["email"] not in repo["stars"]:
            return f"You have not starred '{repo_name}' yet."
        repo["stars"].remove(account["email"])
        account["starred_repos"].remove(repo_name)
        return f"Successfully unstarred '{repo_name}'."
    if name == "git_get_linked_ssh_keys":
        return f"Current linked SSH key:\n{str(account['ssh_keys'])}"
    if name == "git_add_ssh_key":
        if args["ssh_key"] in account["ssh_keys"]:
            return "This SSH key is already added to your account."
        account["ssh_keys"].append(args["ssh_key"])
        return "SSH key successfully added to your account."
    if name == "git_delete_ssh_key":
        if args["ssh_key"] not in account["ssh_keys"]:
            return "This SSH key is not found in your account."
        account["ssh_keys"].remove(args["ssh_key"])
        return "SSH key successfully removed from your account."
    raise KeyError(name)


def execute_github_internal(name: str, state: dict[str, Any], args: dict[str, Any]) -> Any:
    if name != "git_invite_collaborators_wo_verification":
        raise KeyError(name)
    repo = state["github_platform"]["repository_list"].get(args["repo_name"])
    if repo is None:
        return f"Repository '{args['repo_name']}' not found. The link is no longer valid."
    collaborator = args["collaborator_email"]
    if collaborator in repo["collaborators"]:
        return "You have already been a collaborator."
    repo["collaborators"].append(collaborator)
    if collaborator in repo["pending_collaborators"]:
        repo["pending_collaborators"].remove(collaborator)
    return f"You have successfully accepted the invitation to become a collaborator of '{args['repo_name']}'."


def datetime_now() -> str:
    from datetime import datetime

    return str(datetime.now())


GITHUB_TOOLS = {
    "git_create_repo",
    "git_delete_repo",
    "git_transfer_repo_ownership",
    "git_clone",
    "git_invite_collaborators",
    "git_push",
    "git_pull",
    "git_issue",
    "git_star",
    "git_unstar",
    "get_github_linked_unread_emails",
    "get_logged_in_github_user_information",
    "get_github_account_user_information",
    "get_github_repository_information",
    "git_get_linked_ssh_keys",
    "git_add_ssh_key",
    "git_delete_ssh_key",
    "login_github_account",
    "update_github_account_password",
    "verify_github_account",
}
