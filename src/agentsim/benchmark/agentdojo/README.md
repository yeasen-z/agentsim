# AgentDojo benchmark pack

This directory contains benchmark-owned content inside the installable
`agentsim.benchmark` namespace.

Agent Sim owns episode execution:

- hidden state and deterministic tool calls;
- observations and step limits;
- generic `Trace` recording.

This benchmark pack owns:

- AgentDojo environment fixtures and suite configuration;
- user and injection tasks;
- task utility and security evaluation;
- benchmark reports and documentation.

The dependency direction is:

```text
agentsim.benchmark.agentdojo
        │
        ├── uses EnvSim
        ├── uses HiddenState / ToolExecutor / TaskDefine
        └── reads Trace and ground-truth state after an episode

agentsim.core / agentsim.sim
        └── never import benchmark modules
```

Evaluation happens after execution. `evaluate()` invokes the original
AgentDojo task utility/security methods against the pre-state, post-state,
model output, and tool-call history. It does not participate in tool execution
or trace collection.

## Layout

```text
agentdojo/
├── benchmark.yaml
├── attacks.py                # AgentDojo attack registry and payloads
├── run.py                    # AgentSim adapter
├── runner.py                 # single-case and JSONL traversal loop
├── _vendor/                  # AgentDojo 0.1.35 / suite v1.2.2 snapshot
├── docs/
├── AGENTDOJO_LICENSE.md
└── THIRD_PARTY_NOTICES.md
```

The checked-in private snapshot contains the complete AgentDojo v1.2.2 suite
definitions and fixtures. It is an implementation detail and does not create a
runtime dependency on the external `agentdojo` package.

Users enter through one benchmark-level dispatcher instead of importing
same-named factories from individual suite directories:

```python
from agentsim.benchmark import agentdojo

envs = agentdojo.list_envs()
env = next(env for env in envs if env.suite.name == "banking")
tasks = agentdojo.list_tasks(env)
task = tasks[0]

attacks = agentdojo.list_attacks()
clean = agentdojo.build_cases(env, task)[0]
attacked = agentdojo.build_cases(
    env,
    task,
    attack="important_instructions",
    model_name="AI assistant",
)

sim = clean.env
sim.reset(clean.task, instruction=clean.task.description)
# ...agent calls sim.available_tools() and sim.call_tool()...
result = agentdojo.evaluate(sim, clean.task, model_output="...")
```

`attack=None` creates a clean case. Passing one attack returned by
`list_attacks()`—or its name—selects exactly one AgentDojo attack method and
traverses every injection task for the selected user task. For each pair,
canary execution finds every injection vector reachable through the user
task's official tool path, then the selected attack generates the payload
written into all of them. DoS attacks follow AgentDojo and use only one
injection task because their target is utility failure itself.

The Notebook-style traversal is also available without Jupyter:

```python
from datetime import datetime

from agentsim.benchmark import agentdojo

cases = agentdojo.iter_cases(
    suites={"banking"},
    user_task_ids={"user_task_0"},
    attack="important_instructions",
    model_name="AI assistant",
    include_clean=True,
)
records = agentdojo.traverse(
    cases,
    agent_factory,
    output_path=(
        "results/agentdojo-important_instructions-"
        f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.jsonl"
    ),
)
```

`run_case()` executes one case with an `AgentAPI` instance. `traverse()` creates
a fresh agent per case, evaluates the episode, records state diffs and trace
data, and appends one detailed JSON object per case to the JSONL file.
