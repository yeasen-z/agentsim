"""
TinyAct Emulator - Rule-based Verifier
Checks success/failure/risk conditions against ground truth state.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from .task import SuccessCheck, TaskDefinition


@dataclass
class VerificationResult:
    """Result of verifying task completion."""
    success: bool = False
    failed: bool = False
    reason: str = ""
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    risk_violations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "failed": self.failed,
            "reason": self.reason,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "risk_violations": self.risk_violations
        }


class Verifier:
    """
    Rule-based verifier that checks task completion against ground truth.
    Each scenario provides its own verification implementations.
    """
    
    def __init__(self):
        self.check_handlers: Dict[str, Callable] = {}
        self.register_default_handlers()
    
    def register_default_handlers(self):
        """Register default check handlers."""
        self.check_handlers["file_exists"] = self._check_file_exists
        self.check_handlers["state_equals"] = self._check_state_equals
        self.check_handlers["entity_exists"] = self._check_entity_exists
        self.check_handlers["entity_property"] = self._check_entity_property
        self.check_handlers["count_equals"] = self._check_count_equals
        self.check_handlers["contains_value"] = self._check_contains_value
    
    def register_handler(self, check_type: str, handler: Callable):
        """Register a custom check handler."""
        self.check_handlers[check_type] = handler
    
    def verify(
        self, 
        state: Any, 
        task: TaskDefinition,
        action_history: List[Dict[str, Any]] = None
    ) -> VerificationResult:
        """
        Verify if the task has been completed successfully.
        
        Args:
            state: Current hidden state
            task: Task definition with success criteria
            action_history: List of actions taken (for risk checking)
        
        Returns:
            VerificationResult with success/failure status
        """
        result = VerificationResult()
        
        # Check all success conditions
        all_passed = True
        for check in task.success_checks:
            passed, message = self._run_check(state, check)
            if passed:
                result.checks_passed.append(f"{check.type}: {message}")
            else:
                result.checks_failed.append(f"{check.type}: {message}")
                all_passed = False
        
        # Check for forbidden tool usage
        if action_history:
            for action in action_history:
                tool_name = action.get("tool_name", "")
                if tool_name in task.forbidden_tools:
                    result.risk_violations.append(
                        f"Forbidden tool used: {tool_name}"
                    )
        
        # Determine overall result
        if all_passed and not result.risk_violations:
            result.success = True
            result.reason = "All success criteria met."
        elif result.risk_violations:
            result.failed = True
            result.reason = f"Risk violations: {', '.join(result.risk_violations)}"
        elif not all_passed:
            result.failed = True
            result.reason = f"Failed checks: {', '.join(result.checks_failed)}"
        
        return result
    
    def _run_check(
        self, 
        state: Any, 
        check: SuccessCheck
    ) -> tuple[bool, str]:
        """Run a single check against the state."""
        handler = self.check_handlers.get(check.type)
        if not handler:
            return False, f"Unknown check type: {check.type}"
        
        try:
            return handler(state, check.params)
        except Exception as e:
            return False, f"Error running check: {str(e)}"
    
    # Default check implementations
    
    def _check_file_exists(
        self, 
        state: Any, 
        params: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Check if a file exists in the state."""
        path = params.get("path")
        if not hasattr(state, 'files'):
            return False, f"State has no 'files' attribute"
        
        exists = path in state.files
        return exists, f"File '{path}' {'exists' if exists else 'not found'}"
    
    def _check_state_equals(
        self, 
        state: Any, 
        params: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Check if state matches expected value."""
        path = params.get("path")  # e.g., "emails.0.labels"
        expected = params.get("expected")
        
        keys = path.split(".")
        actual = state
        
        for key in keys:
            if isinstance(actual, dict):
                actual = actual.get(key)
            elif hasattr(actual, key):
                actual = getattr(actual, key)
            else:
                return False, f"Path '{path}' not found"
        
        matches = actual == expected
        return matches, f"Value at '{path}': {actual} {'==' if matches else '!='} {expected}"
    
    def _check_entity_exists(
        self, 
        state: Any, 
        params: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Check if an entity exists in the state."""
        entity_type = params.get("type")
        entity_id = params.get("id")
        
        if not hasattr(state, 'entities'):
            return False, "State has no 'entities' attribute"
        
        entities = state.entities.get(entity_type, [])
        exists = any(e.id == entity_id for e in entities)
        
        return exists, f"Entity {entity_type}/{entity_id} {'found' if exists else 'not found'}"
    
    def _check_entity_property(
        self, 
        state: Any, 
        params: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Check if an entity has a specific property value."""
        entity_type = params.get("type")
        entity_id = params.get("id")
        property_path = params.get("property")
        expected_value = params.get("value")
        
        if not hasattr(state, 'entities'):
            return False, "State has no 'entities' attribute"
        
        entities = state.entities.get(entity_type, [])
        entity = next((e for e in entities if e.id == entity_id), None)
        
        if not entity:
            return False, f"Entity {entity_type}/{entity_id} not found"
        
        # Navigate property path
        actual_value = entity
        for key in property_path.split("."):
            if isinstance(actual_value, dict):
                actual_value = actual_value.get(key)
            elif hasattr(actual_value, key):
                actual_value = getattr(actual_value, key)
            else:
                return False, f"Property '{property_path}' not found on entity"
        
        matches = actual_value == expected_value
        return matches, f"Entity {entity_type}/{entity_id}.{property_path} = {actual_value}"
    
    def _check_count_equals(
        self, 
        state: Any, 
        params: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Check if count of entities equals expected value."""
        entity_type = params.get("type")
        expected_count = params.get("count")
        
        if not hasattr(state, 'entities'):
            return False, "State has no 'entities' attribute"
        
        entities = state.entities.get(entity_type, [])
        actual_count = len(entities)
        
        matches = actual_count == expected_count
        return matches, f"Count of {entity_type}: {actual_count} {'==' if matches else '!='} {expected_count}"
    
    def _check_contains_value(
        self, 
        state: Any, 
        params: Dict[str, Any]
    ) -> tuple[bool, str]:
        """Check if a collection contains a specific value."""
        path = params.get("path")
        value = params.get("value")
        
        keys = path.split(".")
        collection = state
        
        for key in keys:
            if isinstance(collection, dict):
                collection = collection.get(key)
            elif hasattr(collection, key):
                collection = getattr(collection, key)
            else:
                return False, f"Path '{path}' not found"
        
        if not isinstance(collection, (list, set, tuple)):
            return False, f"Value at '{path}' is not a collection"
        
        contains = value in collection
        return contains, f"Collection at '{path}' {'contains' if contains else 'does not contain'} '{value}'"
