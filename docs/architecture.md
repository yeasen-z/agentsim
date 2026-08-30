# Repository architecture

Agent Sim separates reusable execution mechanics from benchmark-owned content.

```text
src/agentsim/                  installable package
├── env/                       environment state, tools, and EnvSim
├── agent/                     agent implementations and AgentState
├── task.py                    task and scenario definitions
├── trace/                     append-only trace records
├── interfaces.py              cross-layer protocols and actions
├── registry.py                framework plugin registry
├── scaffold/                  single/multi-agent orchestration
├── runtime.py                 generic episode execution
├── llm_sim/                   optional user/content simulators
benchmarks/
├── common/                    shared benchmark contracts and runner
└── agentdojo/                 concrete benchmark pack and fixtures
    ├── suite modules and task loader
    ├── adapter.py
    ├── _vendor/               private task/tool/data snapshot
    └── docs/

tutorial/
├── scenarios/                 toy environment implementations
└── *.py                       usage examples
```


## Four-layer model

Agent Sim separates four kinds of ownership. They must not share mutable state
implicitly:

1. **`EnvState`** is the authoritative world state. Environment tools may read
   or mutate it. Agents can only see projections produced by the environment's
   observation compiler.
2. **`AgentState`** belongs to one agent. It stores that agent's role, private
   context, conversation history, and working memory; it is not part of the
   simulated world.
3. **Scaffold** owns how one or more agents are assembled and operated. It
   defines topology, prompts, routing, delegation, review, turn scheduling,
   communication, and orchestration budgets. A runtime executes a scaffold; the
   runtime is an execution mechanism, not another state-ownership layer.
4. **`Trace`** is the append-only record of the episode. It observes events
   across the environment, agents, and scaffold without controlling any of
   them.

```text
                  ┌──────────── Trace ────────────┐
                  │ records every boundary event │
                  ▼                              ▼
Scaffold ──selects/routes──> AgentState(s) ──actions──> Env API ──> EnvState
    ▲                                                   │
    └──────── observations and tool results ────────────┘
```

`SingleAgentScaffold` and `MultiAgentScaffold` implement the same `ScaffoldAPI`.
Both are executed by `EpisodeRuntime`; benchmark code does not own a separate
agent loop.

## Dependency rule

`agentsim` framework modules must never import from
`benchmarks` or `tutorial`.

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
- agent actions and tool calls;
- scaffold actor selection, messages, routing, and review outcomes;
- tool results and errors;
- state snapshots after steps;
- timing and episode metadata.

An evaluator belongs to a benchmark because it decides what those facts mean.
It may inspect final state, model output, action history, or trace records to
compute utility and security. Evaluation runs after an episode and may attach a
serializable report to `trace.metadata`; it does not control tool execution or
trace collection.

## Benchmark adapter boundary

Every benchmark implements `BenchmarkAdapter` and evaluates shared
`TaskDefine` and `EvaluationResult` records. `BenchmarkRegistry` discovers
adapters, while each benchmark exposes independent suite environments and a
task loader; the common runner executes each environment/task pair through
`EpisodeRuntime`. Metric names and
evaluator semantics remain benchmark-owned.

AgentDojo is benchmark content, not a second execution framework inside
AgentSim. Its four suites are adapted as `EnvSim` instances; their fixture
loading is implemented by the standard `EnvSim.build_state()` hook; user tasks
are adapted as `TaskDefine` instances; and original tool functions mutate the
suite-specific `EnvState` through AgentSim's `ToolExecutor` boundary.

The private `_vendor` package preserves the versioned AgentDojo definitions and
fixtures needed to reproduce suite `v1.2.2`. Public callers should use only:

```python
import benchmarks.agentdojo as agentdojo

envs = agentdojo.list_envs()
tasks = agentdojo.list_tasks(envs[0])
attacks = agentdojo.list_attacks()
suite_name, task = next(agentdojo.tasks.iter_tasks(
    suites={envs[0].suite.name}, user_task_ids={tasks[0].task_id},
    attack="important_instructions", model_name="AI assistant",
    include_clean=False,
))
env = agentdojo.benchmark.create_env(suite_name)
```

An attacked case is not a different environment type. Before reset, the
adapter executes the user task's official ground-truth read path with canary
values to find all reachable injection vectors. During reset, the selected
attack method generates a payload for each injection task and substitutes it
into those environment-state fields. The agent encounters the payload only if a
tool returns that state content. One run selects one attack method, matching
AgentDojo's benchmark CLI; comparison across attacks belongs in an outer
benchmark campaign.

## Scenario terminology

`ScenarioDefine` is a small framework configuration record. Concrete benchmark
scenarios do not belong in `src/agentsim`; they live under
`benchmarks/<name>`. Teaching scenarios live under
`tutorial/scenarios`.

## Public interfaces

`agentsim.interfaces` contains `Env`, `AgentAPI`, `ScaffoldAPI`,
`RuntimeAPI`, structured `Action`, and `EnvAdapter`.

The `Env` method names are:

- `reset(task, seed, instruction)`;
- `info()`, `tools(agent_id)`, `tool(name, agent_id)`, and `schema(agent_id)`;
- `observe(agent_id)` and `call(..., agent_id)`;
- `done()`, `result()`, `trace()`, and `finish()`.

Agents return a structured `Action` containing `actor_id`. A scaffold selects
actors, supplies private context, routes messages, and applies outcomes.
`EpisodeRuntime` drives the scaffold against the environment and returns a
`RunResult`; benchmark evaluators run afterwards.
