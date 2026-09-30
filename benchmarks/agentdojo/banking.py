"""AgentDojo banking suite environment."""

from .data import load_suite
from .run import DojoEnv

SUITE_NAME = "banking"


def create_env() -> DojoEnv:
    return DojoEnv(load_suite(SUITE_NAME))
