"""InjecAgent data loading and normalization."""

from __future__ import annotations

import ast
import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DATA_DIR = Path(__file__).parent / "data"


@dataclass(frozen=True)
class ToolSpec:
    """A tool specification from InjecAgent."""

    name: str
    toolkit: str
    summary: str
    parameters: List[Dict[str, Any]]
    returns: List[Dict[str, Any]]

    @property
    def full_name(self) -> str:
        return f"{self.toolkit}{self.name}"


@dataclass(frozen=True)
class TestCase:
    """A single InjecAgent test case."""

    case_id: str
    attack_type: str
    user_instruction: str
    user_tool: str
    tool_parameters: Dict[str, Any]
    tool_response: str
    attacker_instruction: str
    attacker_tools: List[str]
    expected_achievements: str

    @classmethod
    def from_raw(cls, raw: Dict[str, Any], index: int, attack_mode: str) -> TestCase:
        return cls(
            case_id=f"{attack_mode}_{index}",
            attack_type=raw.get("Attack Type", "unknown"),
            user_instruction=raw["User Instruction"],
            user_tool=raw["User Tool"],
            tool_parameters=_parse_parameters(raw.get("Tool Parameters", "{}")),
            tool_response=raw["Tool Response"],
            attacker_instruction=raw["Attacker Instruction"],
            attacker_tools=raw.get("Attacker Tools", []),
            expected_achievements=raw.get("Expected Achievements", ""),
        )


def _parse_parameters(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        value = value.strip()
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", SyntaxWarning)
                    parsed = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _decode_serialized(value: Any) -> Any:
    """Decode nested JSON/Python literals used by the upstream data files."""
    parsed = value
    for _ in range(3):
        if not isinstance(parsed, str):
            break
        candidate = parsed.strip()
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", SyntaxWarning)
                    parsed = ast.literal_eval(candidate)
            except (SyntaxError, ValueError):
                break
    if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], str):
        return _decode_serialized(parsed[0])
    return parsed


def _arguments_key(arguments: Dict[str, Any]) -> str:
    return json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str)


def load_attacker_responses() -> Dict[Tuple[str, str], str]:
    """Load well-formed upstream simulated responses by tool and arguments."""
    path = DATA_DIR / "attacker_simulated_responses.json"
    with open(path, "r", encoding="utf-8") as stream:
        raw_responses = json.load(stream)

    responses: Dict[Tuple[str, str], str] = {}
    for invocation, response in raw_responses.items():
        if not invocation.startswith("(") or not invocation.endswith(")"):
            continue
        tool_name, separator, raw_arguments = invocation[1:-1].partition(",")
        if not separator:
            continue
        arguments = _decode_serialized(raw_arguments)
        if not isinstance(arguments, dict):
            continue
        responses.setdefault((tool_name.strip(), _arguments_key(arguments)), response)
    return responses


def load_tools() -> Dict[str, ToolSpec]:
    """Load all tool specifications."""
    tools_path = DATA_DIR / "tools.json"
    with open(tools_path, "r", encoding="utf-8") as f:
        toolkits = json.load(f)

    tools = {}
    for toolkit in toolkits:
        kit_name = toolkit["toolkit"]
        for tool in toolkit.get("tools", []):
            spec = ToolSpec(
                name=tool["name"],
                toolkit=kit_name,
                summary=tool.get("summary", ""),
                parameters=tool.get("parameters", []),
                returns=tool.get("returns", []),
            )
            tools[spec.full_name] = spec
    return tools


def load_test_cases(attack_mode: str = "dh") -> List[TestCase]:
    """Load test cases for the specified attack mode.

    Args:
        attack_mode: "dh" for direct harm, "ds" for data stealing
    """
    filename = f"test_cases_{attack_mode}_base.json"
    path = DATA_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        raw_cases = json.load(f)

    return [TestCase.from_raw(raw, index, attack_mode) for index, raw in enumerate(raw_cases)]


def load_all_test_cases() -> List[TestCase]:
    """Load all test cases from both attack modes."""
    dh_cases = load_test_cases("dh")
    ds_cases = load_test_cases("ds")
    return dh_cases + ds_cases


@dataclass
class InjecAgentData:
    """Container for all InjecAgent data."""

    tools: Dict[str, ToolSpec]
    dh_cases: List[TestCase]
    ds_cases: List[TestCase]
    attacker_responses: Dict[Tuple[str, str], str]

    @classmethod
    def load(cls) -> InjecAgentData:
        return cls(
            tools=load_tools(),
            dh_cases=load_test_cases("dh"),
            ds_cases=load_test_cases("ds"),
            attacker_responses=load_attacker_responses(),
        )

    @property
    def all_cases(self) -> List[TestCase]:
        return self.dh_cases + self.ds_cases

    def attacker_response(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
        return self.attacker_responses.get((tool_name, _arguments_key(arguments)))
