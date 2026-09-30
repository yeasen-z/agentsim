"""Fixed wall clock used by native simulations for repeatable tool results."""

from datetime import datetime

SIMULATION_TIME = datetime(2024, 5, 19, 12, 0, 0)


def simulation_timestamp() -> str:
    return SIMULATION_TIME.isoformat()


def simulation_date() -> str:
    return SIMULATION_TIME.date().isoformat()
