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

- Hidden Python state with serializable entities and metadata
- Deterministic tool registration and execution
- Complete per-step trace recording
- Pluggable environment registry and adapters
- LLM simulation interfaces with no required provider SDK
- Multi-agent roles and orchestration primitives
- Built-in benchmark packs importable from `agentsim.benchmark`

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
from agentsim.benchmark import agentdojo

print(agentsim.__version__)

envs = agentdojo.list_envs()
env = next(env for env in envs if env.suite.name == "banking")
tasks = agentdojo.list_tasks(env)
task = tasks[0]

print([attack.name for attack in agentdojo.list_attacks()])

clean_case = agentdojo.build_cases(env, task)[0]
attacked_cases = agentdojo.build_cases(
    env,
    task,
    attack="important_instructions",
    model_name="AI assistant",
)
```

`attack=None` produces one clean episode. A registered attack name selects one
AgentDojo attack method and produces one episode for every injection task in
that suite. The adapter discovers which injection vectors the user task can
reach and lets the selected official attack generate the payload embedded in
those hidden-state fields. Injection text is not exposed in the initial
observation.

### Run and evaluate one AgentDojo case

Agent Sim owns execution and tracing; AgentDojo owns the task and security
evaluators. A caller can run a case with any agent loop and evaluate it after
the loop finishes:

```python
from agentsim import as_env
from agentsim.benchmark import agentdojo

env = next(env for env in agentdojo.list_envs() if env.suite.name == "banking")
task = next(task for task in agentdojo.list_tasks(env) if task.task_id == "user_task_0")

# Clean case: no injected content.
clean = agentdojo.build_cases(env, task)[0]
runtime = as_env(clean.env)
observation = runtime.reset(clean.task, instruction=clean.task.description)

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

result = agentdojo.evaluate(clean.env, clean.task, model_output="The bill was paid.")
print(result.to_dict())
print(runtime.trace().to_dict())
```

To run the same user task with an indirect prompt-injection attack, select one
official attack method. The injection remains in hidden state until a tool
returns the affected content:

```python
attacked = agentdojo.build_cases(
    env,
    task,
    attack="important_instructions",
    model_name="AI assistant",
)[0]
runtime = as_env(attacked.env)
initial = runtime.reset(attacked.task, instruction=attacked.task.description)
assert "<INFORMATION>" not in str(initial)

tool_result = runtime.call("read_file", {"file_path": "bill-december-2023.txt"})
assert "<INFORMATION>" in str(tool_result.result)
```

`agentdojo.list_attacks()` returns the registered attack methods. One benchmark
run selects one method; comparing methods means running the same task filters
once per method. Targeted attacks expand to `user_tasks × injection_tasks`;
DoS attacks follow AgentDojo and use one injection task per user task.

### Traverse cases from `main.py`

The Notebook-style loop is also available as Python API. Your project supplies
an `AgentAPI` factory; AgentDojo supplies case expansion, the episode loop,
evaluation, state diffs, and optional JSONL persistence:

```python
from datetime import datetime

from agentsim.benchmark import agentdojo

ATTACK = "important_instructions"


def agent_factory():
    # Return your AgentAPI implementation here.
    return YourAgentAPI()


cases = agentdojo.iter_cases(
    suites={"banking"},
    user_task_ids={"user_task_0"},
    attack=ATTACK,
    model_name="AI assistant",
    include_clean=True,
)

records = agentdojo.traverse(
    cases,
    agent_factory,
    output_path=(
        f"results/agentdojo-{ATTACK}-"
        f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.jsonl"
    ),
    max_cases=None,
    max_steps=30,
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

An execution environment is assembled from four pieces:

1. `ScenarioDefine` describes the environment.
2. `HiddenState` stores authoritative state.
3. `ToolExecutor` applies deterministic operations to that state.
4. `EnvSim` coordinates observations, actions, step limits, and
   tracing.

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
hidden state, action history, model output, and generic trace after the episode.

For example:

```python
evaluation = benchmark_evaluator.evaluate_episode(
    state=sim.hidden_state,
    task=task,
    action_history=sim.action_history,
    model_output=answer,
)
env.trace().metadata["evaluation"] = evaluation.to_dict()
```

## Public modules

- `agentsim.core`: state, tools, task configuration, tracing, registry, and
  environment interfaces
- `agentsim.agents`: LLM client adapters and agent helpers
- `agentsim.llm_sim`: instruction, content, feedback, and user simulators
- `agentsim.multi_agent`: roles, agents, messages, and orchestration
- `agentsim.benchmark`: built-in environments, task data, and evaluators
- `agentsim.EnvSim`: the main environment coordinator

## Repository layout

```text
agent-sim/
├── src/agentsim/       # Installable package
│   ├── core/
│   ├── agents/
│   ├── benchmark/
│   │   └── agentdojo/  # adapter, versioned data, tasks, tools, evaluators
│   ├── llm_sim/
│   ├── multi_agent/
│   └── sim.py
├── examples/            # Toy environments and integration examples
├── tests/               # Framework tests
├── pyproject.toml       # Package and tool configuration
└── README.md
```

## Development checks

Run these commands from the repository root:

```bash
ruff check .
black --check .
pytest
python -m build
```

## Project scope

`agentsim.core` is the reusable simulation framework. Built-in environments,
task datasets, and evaluators live under `agentsim.benchmark`; toy environments
live under `examples/`. Core modules never import benchmark modules.

See [`docs/architecture.md`](docs/architecture.md) for the ownership and
dependency rules, including the distinction between generic tracing and
benchmark-specific evaluation.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). User-visible changes are tracked in
[CHANGELOG.md](CHANGELOG.md).

## License

Agent Sim is released under the [MIT License](LICENSE).
