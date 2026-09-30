"""AgentDojo travel suite environment."""

from .data import load_suite
from .run import DojoEnv

SUITE_NAME = "travel"


def create_env() -> DojoEnv:
    return DojoEnv(load_suite(SUITE_NAME))
