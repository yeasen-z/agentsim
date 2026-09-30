"""Backward-compatible exports for the shared native attack catalog."""

from benchmarks.common.attacks import (
    DEFAULT_MODEL_NAME,
    DEFAULT_USER_NAME,
    KNOWN_MODEL_NAMES,
    Attack,
    list_attacks,
    resolve_attack,
)

__all__ = [
    "DEFAULT_MODEL_NAME",
    "DEFAULT_USER_NAME",
    "KNOWN_MODEL_NAMES",
    "Attack",
    "list_attacks",
    "resolve_attack",
]
