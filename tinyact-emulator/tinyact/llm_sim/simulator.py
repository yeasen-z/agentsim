"""
TinyAct Emulator - LLM-based Simulator
Generates natural language complexity: instructions, content, feedback.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import random


@dataclass
class InstructionVariant:
    """A variant of task instruction."""
    text: str
    style: str  # direct, vague, conversational, formal
    difficulty: str  # easy, medium, hard


class InstructionGenerator:
    """
    Generates natural language task instructions.
    Can use templates or LLM for variety.
    """
    
    def __init__(self, seed: int = None):
        self.rng = random.Random(seed)
        self.variants: Dict[str, List[InstructionVariant]] = {}
    
    def add_variant(self, task_id: str, variant: InstructionVariant):
        """Add an instruction variant for a task."""
        if task_id not in self.variants:
            self.variants[task_id] = []
        self.variants[task_id].append(variant)
    
    def generate(
        self, 
        task_id: str, 
        hidden_goal: Dict[str, Any],
        style: str = None
    ) -> str:
        """
        Generate an instruction for a task.
        
        Args:
            task_id: Task identifier
            hidden_goal: Hidden goal dictionary
            style: Preferred style (optional)
        
        Returns:
            Natural language instruction
        """
        if task_id in self.variants and self.variants[task_id]:
            variants = self.variants[task_id]
            if style:
                matching = [v for v in variants if v.style == style]
                if matching:
                    return self.rng.choice(matching).text
            return self.rng.choice(variants).text
        
        # Default: generate from template
        return self._generate_from_template(task_id, hidden_goal)
    
    def _generate_from_template(
        self, 
        task_id: str, 
        hidden_goal: Dict[str, Any]
    ) -> str:
        """Generate instruction from hidden goal using templates."""
        action = hidden_goal.get("action", "complete the task")
        
        templates = {
            "save_attachment": [
                f"Save the attachment from the email.",
                f"Download the file attached to the message.",
                f"Can you grab that attachment and store it?",
                f"I need you to archive the attachment from this email."
            ],
            "update_status": [
                f"Update the status as requested.",
                f"Change the current status.",
                f"Please mark this with the appropriate status.",
                f"The status needs to be updated."
            ],
            "search": [
                f"Find what I'm looking for.",
                f"Search for the relevant items.",
                f"Can you look this up?",
                f"I need you to find something."
            ],
            "create": [
                f"Create a new item.",
                f"Make a new entry.",
                f"Please add this.",
                f"I need you to create something."
            ]
        }
        
        action_templates = templates.get(action, templates["create"])
        return self.rng.choice(action_templates)


class ContentGenerator:
    """
    Generates realistic content: emails, notes, descriptions.
    """
    
    def __init__(self, seed: int = None):
        self.rng = random.Random(seed)
    
    def generate_email_body(
        self,
        sender: str,
        subject: str,
        topic: str,
        has_attachment: bool = False
    ) -> str:
        """Generate realistic email body."""
        greetings = [
            "Hi there,",
            "Hello,",
            "Dear colleague,",
            "Good morning,",
            ""
        ]
        
        bodies = [
            f"I'm writing regarding {topic}. Please find the details below.",
            f"This is about {topic}. Let me know if you have questions.",
            f"Following up on {topic}. See attached for more information.",
            f"Quick note about {topic}. Thanks!",
        ]
        
        closings = [
            "Best regards,",
            "Thanks,",
            "Cheers,",
            "Best,",
            ""
        ]
        
        greeting = self.rng.choice(greetings)
        body = self.rng.choice(bodies)
        closing = self.rng.choice(closings)
        
        attachment_note = "Attachment included." if has_attachment else ""
        
        return f"{greeting}\n\n{body}\n\n{attachment_note}\n{closing}\n{sender}"
    
    def generate_note(
        self,
        author: str,
        topic: str
    ) -> str:
        """Generate a realistic note."""
        templates = [
            f"Note: {topic}. - {author}",
            f"Reminder: {topic}",
            f"FYI: {topic}",
            f"Important: {topic}. Contact: {author}",
        ]
        return self.rng.choice(templates)
    
    def generate_description(
        self,
        entity_type: str,
        details: Dict[str, Any]
    ) -> str:
        """Generate a description for an entity."""
        if entity_type == "customer":
            name = details.get("name", "Unknown")
            company = details.get("company", "Unknown Corp")
            return f"Customer: {name} from {company}"
        
        elif entity_type == "file":
            name = details.get("name", "unnamed")
            size = details.get("size", "unknown")
            return f"File: {name} ({size})"
        
        return f"{entity_type}: {details}"


class FeedbackGenerator:
    """
    Generates natural language feedback for actions.
    """
    
    def __init__(self, seed: int = None):
        self.rng = random.Random(seed)
    
    def generate_success_feedback(
        self,
        tool_name: str,
        result: Any
    ) -> str:
        """Generate feedback for successful action."""
        templates = [
            f"Successfully executed {tool_name}.",
            f"{tool_name} completed.",
            f"Done: {tool_name}.",
            f"The {tool_name} operation was successful.",
        ]
        return self.rng.choice(templates)
    
    def generate_error_feedback(
        self,
        tool_name: str,
        error: str
    ) -> str:
        """Generate feedback for failed action."""
        templates = [
            f"Error executing {tool_name}: {error}",
            f"{tool_name} failed: {error}",
            f"Could not complete {tool_name}. Error: {error}",
        ]
        return self.rng.choice(templates)
    
    def generate_clarification_request(
        self,
        context: str
    ) -> str:
        """Generate a clarification request."""
        templates = [
            "Could you clarify what you mean?",
            "I need more information to proceed.",
            "Can you provide more details?",
            "I'm not sure I understand. Could you rephrase?",
        ]
        return self.rng.choice(templates)


class UserSimulator:
    """
    Simulates user interactions: follow-ups, corrections, clarifications.
    """
    
    def __init__(self, seed: int = None):
        self.rng = random.Random(seed)
        self.instruction_generator = InstructionGenerator(seed)
        self.feedback_generator = FeedbackGenerator(seed)
    
    def generate_followup(
        self,
        original_instruction: str,
        agent_action: str
    ) -> Optional[str]:
        """Generate a user follow-up message."""
        followups = [
            "Actually, can you also check something else?",
            "Wait, I think there's a better way.",
            "That's good, but I also need...",
            "Hmm, let me think about this.",
            None,  # No followup
        ]
        return self.rng.choice(followups)
    
    def generate_correction(
        self,
        agent_action: str,
        expected_action: str
    ) -> str:
        """Generate a correction when agent makes a mistake."""
        templates = [
            f"That's not quite right. I expected {expected_action}.",
            f"Actually, I need you to {expected_action} instead.",
            f"Wrong approach. Please try {expected_action}.",
        ]
        return self.rng.choice(templates)
