from agentsim.benchmark.agentdojo._vendor.default_suites.v1.workspace.injection_tasks import WorkspaceInjectionTask  # noqa: F401 - Register tasks
from agentsim.benchmark.agentdojo._vendor.default_suites.v1.workspace.task_suite import task_suite as workspace_task_suite
from agentsim.benchmark.agentdojo._vendor.default_suites.v1.workspace.user_tasks import WorkspaceUserTask  # noqa: F401 - Register tasks

__all__ = ["workspace_task_suite"]
