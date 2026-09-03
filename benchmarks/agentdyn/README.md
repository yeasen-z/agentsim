# AgentDyn

AgentDyn is a native AgentSim adaptation of the AgentDyn benchmark's dynamic
multi-application setting. It exposes independent `shopping`, `github`, and
`dailylife` suites through the standard `EnvSim` contract. YAML fixtures are
loaded at runtime (including their `!include` files), while normalized task,
tool-schema, and ground-truth records are stored as inert JSON. Execution uses
the deterministic AgentSim environment in `env.py`, so traces and state stay
under AgentSim's control; no upstream Python runtime is imported.

```python
from benchmarks.agentdyn import benchmark, iter_tasks

suite, task = next(iter_tasks(suites=["shopping"]))
env = benchmark.create_env(suite)
```

The adapter reports benign utility, attack success rate, security, and secure
utility. New benchmark records should be added to the suite data and kept
independent of the upstream package implementation.
