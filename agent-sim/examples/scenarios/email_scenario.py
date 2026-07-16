"""
Example: Custom Email Management Scenario

Demonstrates how to create a pluggable custom simulation environment
with state initialization, tool registration, and verification.
"""
from typing import Any, Dict, List
from dataclasses import dataclass, field

import sys
sys.path.insert(0, '/workspace/agent-sim')

from agent_sim.core import (
    HiddenState, 
    ToolExecutor, 
    ToolDefinition,
    ToolRiskLevel,
    Verifier,
    VerificationResult,
    TaskDefinition,
    SuccessCheck,
    registry,
    register
)


# ============================================================================
# State Definitions
# ============================================================================

@dataclass
class Email:
    """Represents an email in the inbox."""
    id: str
    subject: str
    sender: str
    body: str
    labels: List[str] = field(default_factory=list)
    is_read: bool = False
    is_archived: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "sender": self.sender,
            "body": self.body,
            "labels": self.labels,
            "is_read": self.is_read,
            "is_archived": self.is_archived
        }


@dataclass
class EmailState(HiddenState):
    """Hidden state for the email management scenario."""
    emails: Dict[str, Email] = field(default_factory=dict)
    folders: Dict[str, List[str]] = field(default_factory=lambda: {
        "inbox": [],
        "sent": [],
        "drafts": [],
        "trash": []
    })
    
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base["emails"] = {k: v.to_dict() for k, v in self.emails.items()}
        base["folders"] = self.folders
        return base


# ============================================================================
# Scenario Components
# ============================================================================

def init_email_state(seed_data: Dict[str, Any], seed: int = 42) -> HiddenState:
    """Initialize the email state from seed data."""
    state = EmailState()
    
    # Create initial emails
    initial_emails = seed_data.get("emails", [
        {"id": "email_1", "subject": "Meeting Tomorrow", "sender": "boss@example.com", "body": "Let's meet at 3pm"},
        {"id": "email_2", "subject": "Project Update", "sender": "team@example.com", "body": "Weekly status report"},
        {"id": "email_3", "subject": "Lunch Plans", "sender": "friend@example.com", "body": "Want to grab lunch?"},
    ])
    
    for email_data in initial_emails:
        email = Email(**email_data)
        state.emails[email.id] = email
        state.folders["inbox"].append(email.id)
    
    return state


def register_email_tools(executor: ToolExecutor):
    """Register all tools for the email scenario."""
    
    # Tool: list_emails
    def list_emails(state: EmailState, folder: str = "inbox") -> List[Dict[str, Any]]:
        """List emails in a folder."""
        if folder not in state.folders:
            raise ValueError(f"Unknown folder: {folder}")
        
        email_ids = state.folders[folder]
        return [state.emails[eid].to_dict() for eid in email_ids if eid in state.emails]
    
    executor.register_tool(
        name="list_emails",
        func=list_emails,
        definition=ToolDefinition(
            name="list_emails",
            description="List emails in a specified folder",
            parameters={
                "type": "object",
                "properties": {
                    "folder": {
                        "type": "string",
                        "description": "Folder name (inbox, sent, drafts, trash)",
                        "default": "inbox"
                    }
                }
            },
            category="read"
        )
    )
    
    # Tool: read_email
    def read_email(state: EmailState, email_id: str) -> Dict[str, Any]:
        """Read an email and mark it as read."""
        if email_id not in state.emails:
            raise ValueError(f"Email not found: {email_id}")
        
        email = state.emails[email_id]
        email.is_read = True
        return email.to_dict()
    
    executor.register_tool(
        name="read_email",
        func=read_email,
        definition=ToolDefinition(
            name="read_email",
            description="Read an email by ID and mark it as read",
            parameters={
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "The ID of the email to read"
                    }
                },
                "required": ["email_id"]
            },
            category="read"
        )
    )
    
    # Tool: send_email
    def send_email(
        state: EmailState, 
        to: str, 
        subject: str, 
        body: str
    ) -> Dict[str, Any]:
        """Send a new email."""
        import uuid
        email_id = f"email_{uuid.uuid4().hex[:6]}"
        
        email = Email(
            id=email_id,
            subject=subject,
            sender="user@example.com",
            body=body,
            is_read=True
        )
        state.emails[email_id] = email
        state.folders["sent"].append(email_id)
        
        return {"success": True, "email_id": email_id}
    
    executor.register_tool(
        name="send_email",
        func=send_email,
        definition=ToolDefinition(
            name="send_email",
            description="Send a new email",
            parameters={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject"},
                    "body": {"type": "string", "description": "Email body"}
                },
                "required": ["to", "subject", "body"]
            },
            category="write",
            risk_level=ToolRiskLevel.MODERATE
        )
    )
    
    # Tool: archive_email
    def archive_email(state: EmailState, email_id: str) -> Dict[str, Any]:
        """Archive an email (move from inbox to archives)."""
        if email_id not in state.emails:
            raise ValueError(f"Email not found: {email_id}")
        
        # Remove from inbox
        if email_id in state.folders["inbox"]:
            state.folders["inbox"].remove(email_id)
        
        state.emails[email_id].is_archived = True
        
        return {"success": True, "archived": email_id}
    
    executor.register_tool(
        name="archive_email",
        func=archive_email,
        definition=ToolDefinition(
            name="archive_email",
            description="Archive an email (remove from inbox)",
            parameters={
                "type": "object",
                "properties": {
                    "email_id": {
                        "type": "string",
                        "description": "The ID of the email to archive"
                    }
                },
                "required": ["email_id"]
            },
            category="organize"
        )
    )
    
    # Tool: add_label
    def add_label(state: EmailState, email_id: str, label: str) -> Dict[str, Any]:
        """Add a label to an email."""
        if email_id not in state.emails:
            raise ValueError(f"Email not found: {email_id}")
        
        if label not in state.emails[email_id].labels:
            state.emails[email_id].labels.append(label)
        
        return {"success": True, "email_id": email_id, "label": label}
    
    executor.register_tool(
        name="add_label",
        func=add_label,
        definition=ToolDefinition(
            name="add_label",
            description="Add a label/tag to an email",
            parameters={
                "type": "object",
                "properties": {
                    "email_id": {"type": "string", "description": "Email ID"},
                    "label": {"type": "string", "description": "Label to add"}
                },
                "required": ["email_id", "label"]
            },
            category="organize"
        )
    )


def create_email_verifier() -> Verifier:
    """Create a verifier for email scenarios."""
    verifier = Verifier()
    
    # Register custom check handler
    def check_email_has_label(state: EmailState, params: Dict[str, Any]) -> tuple[bool, str]:
        email_id = params.get("email_id")
        expected_label = params.get("label")
        
        if email_id not in state.emails:
            return False, f"Email {email_id} not found"
        
        has_label = expected_label in state.emails[email_id].labels
        return has_label, f"Email {email_id} {'has' if has_label else 'does not have'} label '{expected_label}'"
    
    verifier.register_handler("email_has_label", check_email_has_label)
    
    return verifier


def compile_email_observation(state: EmailState, task: TaskDefinition) -> Dict[str, Any]:
    """Compile the hidden state into an observation for the agent."""
    # Only show unread emails count and folder summaries
    inbox_count = len(state.folders.get("inbox", []))
    unread_count = sum(1 for e in state.emails.values() if not e.is_read)
    
    return {
        "inbox_email_count": inbox_count,
        "unread_count": unread_count,
        "folders": {k: len(v) for k, v in state.folders.items()},
        "hint": "Use list_emails to see email details"
    }


# ============================================================================
# Setup Function (called by registry)
# ============================================================================

def setup():
    """
    Setup function that returns all scenario components.
    This is the entry point for the scenario registry.
    """
    return (
        init_email_state,      # state_initializer
        register_email_tools,  # tool_registrar
        create_email_verifier, # verifier_factory
        compile_email_observation  # observation_compiler
    )


# ============================================================================
# Alternative: Decorator-based Registration
# ============================================================================

@register(
    id="email_management_v2",
    name="Email Management V2",
    description="Alternative email scenario using decorator registration",
    tags=["email", "productivity", "example"]
)
def email_scenario_v2():
    """Alternative way to register the same scenario using decorator."""
    return setup()


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Register the scenario
    registry.register(
        id="email_management",
        name="Email Management",
        description="A realistic email inbox simulation scenario",
        module_path=__name__,
        state_initializer=init_email_state,
        tool_registrar=register_email_tools,
        verifier_factory=create_email_verifier,
        observation_compiler=compile_email_observation,
        tags=["email", "productivity", "example"]
    )
    
    print("Registered scenarios:", registry.list_scenarios())
    
    # Get the registered scenario
    plugin = registry.get("email_management")
    print(f"\nScenario: {plugin.name}")
    print(f"Description: {plugin.description}")
    print(f"Tags: {plugin.tags}")
    
    # Create a tool executor and register tools
    executor = ToolExecutor()
    plugin.tool_registrar(executor)
    
    print(f"\nAvailable tools: {[t.name for t in executor.get_available_tools()]}")
    
    # Initialize state
    state = plugin.state_initializer({}, seed=42)
    print(f"\nInitial state: {len(state.emails)} emails in inbox")
    
    # Create verifier
    verifier = plugin.verifier_factory()
    print(f"Verifier handlers: {list(verifier.check_handlers.keys())}")
