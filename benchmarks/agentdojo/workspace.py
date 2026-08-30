"""AgentDojo workspace suite environment."""
from ._vendor.task_suite.load_suites import get_suites
from .run import BENCHMARK_VERSION, DojoEnv
SUITE_NAME = "workspace"
def create_env() -> DojoEnv:
    return DojoEnv(get_suites(BENCHMARK_VERSION)[SUITE_NAME])
