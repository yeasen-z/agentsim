# Agent Sim

Agent Sim is a Python framework for building deterministic, inspectable
environments for developing and evaluating tool-using agents.

Its core design rule is simple:

> Python maintains ground truth; language models add semantic realism.

State transitions and tool effects remain deterministic. Benchmark-owned
evaluators inspect ground truth and traces after execution.

> Status: Agent Sim is an early-stage framework. The core APIs are usable, but
> they may change before a stable 1.0 release.

## Features

- Authoritative environment state with serializable entities and metadata
- Deterministic tool registration and execution
- Append-only environment, agent, scaffold, and runtime event tracing
- Pluggable environment registry and adapters
- LLM simulation interfaces with no required provider SDK
- Single- and multi-agent scaffolds on one runtime contract
- Built-in benchmark packs importable from `benchmarks.common`

## Requirements

- Python 3.10 or newer

## Installation

Install the package from a local checkout:

```bash
git clone https://github.com/yeasen-z/agent-sim.git
cd agent-sim
python -m pip install .
```

## Use as a dependency

Keep application code in a separate project and install Agent Sim into that
project's virtual environment:

```text
your-agent-project/
├── main.py
└── agent-sim/
```

```bash
cd your-agent-project
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ./agent-sim
```

Application code can then import the installed package normally:

```python
import agentsim
from agentsim import EnvSim
import benchmarks.agentdojo as agentdojo

print(agentsim.__version__)

envs = agentdojo.list_envs()
env = next(env for env in envs if env.suite.name == "banking")
tasks = agentdojo.list_tasks(env)
task = tasks[0]

print([attack.name for attack in agentdojo.list_attacks()])

suite_name, clean_task = next(agentdojo.tasks.iter_tasks(
    suites={"banking"}, user_task_ids={task.task_id}
))
attacked_tasks = list(agentdojo.tasks.iter_tasks(
    suites={"banking"}, user_task_ids={task.task_id},
    attack="important_instructions", model_name="AI assistant", include_clean=False,
))
```

`attack=None` produces one clean episode. A registered attack name selects one
AgentDojo attack method and produces one episode for every injection task in
that suite. The adapter discovers which injection vectors the user task can
reach and lets the selected official attack generate the payload embedded in
those environment-state fields. Injection text is not exposed in the initial
observation.

### Run and evaluate one AgentDojo case

Agent Sim owns execution, tracing, and benchmark evaluation; AgentDojo supplies
the versioned task content and security semantics. The low-level environment API is also available for manual
debugging before using the shared scaffold runtime:

```python
from agentsim import as_env
import benchmarks.agentdojo as agentdojo

env = next(env for env in agentdojo.list_envs() if env.suite.name == "banking")
task = next(task for task in agentdojo.list_tasks(env) if task.task_id == "user_task_0")

# Clean case: no injected content.
suite_name, clean = next(agentdojo.tasks.iter_tasks(
    suites={"banking"}, user_task_ids={"user_task_0"}
))
sim = agentdojo.benchmark.create_env(suite_name)
runtime = as_env(sim)
observation = runtime.reset(clean, instruction=clean.description)

# This is where your agent loop chooses tool calls.
runtime.call("read_file", {"file_path": "bill-december-2023.txt"})
runtime.call(
    "send_money",
    {
        "recipient": "UK12345678901234567890",
        "amount": 98.70,
        "subject": "Car Rental\t\t\t98.70",
        "date": "2022-01-01",
    },
)

result = agentdojo.evaluate(sim, clean, model_output="The bill was paid.")
print(result.to_dict())
print(runtime.trace().to_dict())
```

To run the same user task with an indirect prompt-injection attack, select one
official attack method. The injection remains in environment state until a tool
returns the affected content:

```python
suite_name, attacked = next(agentdojo.tasks.iter_tasks(
    suites={"banking"}, user_task_ids={"user_task_0"},
    attack="important_instructions", model_name="AI assistant", include_clean=False,
))
runtime = as_env(agentdojo.benchmark.create_env(suite_name))
initial = runtime.reset(attacked, instruction=attacked.description)
assert "<INFORMATION>" not in str(initial)

tool_result = runtime.call("read_file", {"file_path": "bill-december-2023.txt"})
assert "<INFORMATION>" in str(tool_result.result)
```

`agentdojo.list_attacks()` returns the registered attack methods. One benchmark
run selects one method; comparing methods means running the same task filters
once per method. Targeted attacks expand to `user_tasks × injection_tasks`;
DoS attacks follow AgentDojo and use one injection task per user task.

### Traverse cases from `main.py`

The traversal API accepts a scaffold factory. The same benchmark path therefore
runs either a single agent or a multi-agent scaffold:

```python
from datetime import datetime

from agentsim import LLMAdapter, SingleAgentScaffold
import benchmarks.agentdojo as agentdojo

ATTACK = "important_instructions"


def scaffold_factory():
    agent = LLMAdapter(YourLLMClient(), agent_id="assistant")
    return SingleAgentScaffold(agent, max_turns=30)


tasks = agentdojo.iter_suite_tasks(
    suites={"banking"},
    user_task_ids={"user_task_0"},
    attack=ATTACK,
    model_name="AI assistant",
    include_clean=True,
)

records = agentdojo.traverse(
    tasks,
    scaffold_factory,
    output_path=(
        f"results/agentdojo-{ATTACK}-"
        f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.jsonl"
    ),
    max_tasks=None,
    max_scaffold_turns=30,
)

print(len(records))
```

For the example filters this runs one clean case plus all injection tasks for
the selected attack. Set `attack=None` for clean-only traversal, or change
`ATTACK` and rerun to compare another registered attack. The returned list
contains lightweight summaries; each detailed case is written immediately to
the JSONL file.

Do not modify `sys.path` to import the package. An editable install makes local
framework changes immediately available to the application.

## Core model

Agent Sim separates four ownership layers:

1. `EnvState` stores the authoritative simulated world.
2. `AgentState` stores one agent's private context and working memory.
3. A scaffold defines agent topology, prompts, communication, delegation,
   review, scheduling, and orchestration budgets.
4. `Trace` records environment, agent, and scaffold events without controlling
   them.

`ScenarioDefine`, `ToolExecutor`, and `EnvSim` implement the environment layer.
A runtime drives a scaffold against the environment; it is an execution
mechanism rather than a fifth state layer.

The primary interaction loop is:

```python
from agentsim import EnvSim, as_env

sim = EnvSim(
    scenario=scenario,
    init_state=init_state,
    executor=executor,
)
env = as_env(sim)

observation = env.reset(task, seed=42, instruction="Complete the task")
available = env.tools()
result = env.call("tool_name", {"argument": "value"})
trace = env.trace()
```

`EnvSim` is configured with a scenario, state initializer, tool executor, and
optional observation compiler. `as_env()` exposes the compact `Env` API. Neither
knows whether a benchmark task succeeded. Benchmark code evaluates the final
environment state, tool history, model output, and generic trace after the episode.

For example:

```python
evaluation = benchmark_evaluator.evaluate_episode(
    state=sim.env_state,
    task=task,
    tool_history=sim.tool_history,
    model_output=answer,
)
env.trace().metadata["evaluation"] = evaluation.to_dict()
```

## Public modules

- `agentsim.env`: environment layer. `EnvState` is the authoritative simulated
  world; `EnvSim` owns reset/observe/tool-call lifecycle; `env.tool` defines
  deterministic tools and their results.
- `agentsim.agent`: agent implementations and private `AgentState`. This layer
  contains single agents, manager/worker/reviewer roles, LLM clients, and
  message objects. Agent state is never the environment world state.
- `agentsim.task`: `TaskDefine`, `ScenarioDefine`, and success-check records.
  These describe what should be executed, not how the environment executes it.
- `agentsim.scaffold`: single- and multi-agent orchestration. A scaffold owns
  topology, prompts, scheduling, messaging, delegation, and review.
- `agentsim.trace`: append-only `Trace` and `TraceEvent` records for facts from
  the environment, agents, and scaffold.
- `agentsim.interfaces`: shared protocols (`Env`, `AgentAPI`, `ScaffoldAPI`,
  `RuntimeAPI`) and structured actions/results used at layer boundaries.
- `agentsim.runtime`: `EpisodeRuntime`, the generic loop that connects one
  scaffold to one environment for one task.
- `agentsim.llm_sim`: optional instruction, content, feedback, and user
  simulators used by agents.
- `benchmarks.common`: generic benchmark contracts, evaluation results,
  registry, and task traversal. It is repository-level infrastructure, not part
  of the installable AgentSim package.
- `agentsim.registry`: framework plugin/scenario registry.

## Repository layout

```text
agentsim/
├── src/agentsim/       # Installable package
│   ├── env/
│   ├── agent/
│   ├── task.py
│   ├── trace/
│   ├── interfaces.py
│   ├── registry.py
│   ├── llm_sim/
│   ├── scaffold/
│   └── runtime.py
├── benchmarks/         # concrete benchmark packs and fixtures
│   └── common/          # shared benchmark contracts and runner
├── pyproject.toml       # Package and tool configuration
└── README.md
```

### How one episode flows

```text
TaskDefine
    │
    ▼
EpisodeRuntime ── runs ──> Scaffold ── selects/actions ──> Env
       │                       │                           │
       └────────────── records events in Trace ◄───────────┘
```

The environment owns the world, each agent owns only its private state, the
scaffold coordinates one or more agents, and the trace records what happened.
Benchmark code supplies tasks and scoring rules after the episode; it does not
replace the runtime or create a second execution loop.

## Development checks

Run these commands from the repository root:

```bash
ruff check .
black --check .
python -m build
```

## Project scope

`src/agentsim` is the reusable simulation framework. Concrete benchmark
datasets and evaluators live under `benchmarks/`. Core modules never import
benchmark modules.

See [`docs/architecture.md`](docs/architecture.md) for the ownership and
dependency rules, including the distinction between generic tracing and
benchmark-specific evaluation.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). User-visible changes are tracked in
[CHANGELOG.md](CHANGELOG.md).

## License

Agent Sim is released under the [MIT License](LICENSE).
