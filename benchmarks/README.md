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
