"""AgentDyn Daily Life suite."""

from .env import AgentDynEnv


def create_env() -> AgentDynEnv:
    return AgentDynEnv("dailylife")
