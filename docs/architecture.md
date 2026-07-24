# Repository architecture

Agent Sim separates reusable execution mechanics from benchmark-owned content.

```text
src/agentsim/                  installable package
├── core/                      reusable framework
│   ├── state.py                generic hidden state
│   ├── tool.py                 deterministic tool runtime
│   ├── task.py                 task/scenario configuration records
│   ├── trace.py                generic episode trace
│   ├── registry.py             environment discovery
│   └── interfaces.py           canonical env/agent/runtime contracts
├── sim.py                      reset / observe / call_tool / step budget
└── benchmark/                  built-in benchmark content
    └── agentdojo/
        ├── benchmark.yaml
        ├── run.py              AgentSim adapter and AgentDojo-owned scoring
        ├── _vendor/            private v1.2.2 task/tool/data snapshot
        └── docs/

examples/
├── scenarios/                  toy environment implementations
└── *.py                        usage examples
```

## Dependency rule

`agentsim.core` and `agentsim.sim` must never import from
`agentsim.benchmark` or `examples`.

Built-in benchmark modules may import the framework:

```text
benchmark environment ─┐
benchmark evaluator ───┼──> agentsim
benchmark runner ──────┘
```

## Trace versus evaluation

Trace collection is part of execution and is independent of the task's scoring
rules. Every environment records the same categories of facts:

- initial state snapshot;
- observations;
- actions and tool calls;
- tool results and errors;
- state snapshots after steps;
- timing and episode metadata.

An evaluator belongs to a benchmark because it decides what those facts mean.
It may inspect final state, model output, action history, or trace records to
compute utility and security. Evaluation runs after an episode and may attach a
serializable report to `trace.metadata`; it does not control tool execution or
trace collection.

## Benchmark adapter boundary

AgentDojo is benchmark content, not a second execution framework inside
AgentSim. Its four suites are adapted as `EnvSim` instances; its user tasks are
adapted as `TaskDefine` instances; and its original tool functions mutate an
AgentSim `HiddenState` through `ToolExecutor`.

The private `_vendor` package preserves the versioned AgentDojo definitions and
fixtures needed to reproduce suite `v1.2.2`. Public callers should use only:

```python
from agentsim.benchmark import agentdojo

envs = agentdojo.list_envs()
tasks = agentdojo.list_tasks(envs[0])
attacks = agentdojo.list_attacks()
cases = agentdojo.build_cases(
    envs[0],
    tasks[0],
    attack="important_instructions",
    model_name="AI assistant",
)
```

An attacked case is not a different environment type. Before reset, the
adapter executes the user task's official ground-truth read path with canary
values to find all reachable injection vectors. During reset, the selected
attack method generates a payload for each injection task and substitutes it
into those hidden-state fields. The agent encounters the payload only if a
tool returns that state content. One run selects one attack method, matching
AgentDojo's benchmark CLI; comparison across attacks belongs in an outer
benchmark campaign.

## Scenario terminology

`ScenarioDefine` is a small framework configuration record. Concrete benchmark
scenarios do not belong in `agentsim.core`; they live under
`agentsim.benchmark.<name>`. Teaching scenarios live under
`examples/scenarios`.

## Public interfaces

`agentsim.core.interfaces` is the only source of interface definitions.
It contains `Env`, `AgentAPI`, `RuntimeAPI`, and `EnvAdapter`.

The `Env` method names are:

- `reset(task, seed, instruction)`;
- `info()`, `tools()`, `tool()`, and `schema()`;
- `observe()` and `call()`;
- `done()`, `result()`, and `trace()`.

Agents implement `act(...)` and `reset()`. Runtimes connect an agent to an
environment and return execution facts; benchmark evaluators run afterwards.
