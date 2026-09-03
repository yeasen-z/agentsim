# Benchmarks

This directory contains concrete benchmark implementations and their fixtures.
They are kept outside `src/agentsim` so the framework package remains focused on
the shared environment, agent, scaffold, trace, runtime, and benchmark-runner
contracts.

AgentDojo can be used from a repository checkout with:

```python
import benchmarks.agentdojo as agentdojo
```

The reusable benchmark interfaces and generic runner remain in
`benchmarks.common`.

AgentDyn is available as an independent native suite package:

```python
import benchmarks.agentdyn as agentdyn

for suite, task in agentdyn.iter_tasks(suites=["shopping"]):
    env = agentdyn.benchmark.create_env(suite)
```

Its `shopping`, `github`, and `dailylife` environments share only the common
AgentSim contract; each suite has its own factory and task stream.
