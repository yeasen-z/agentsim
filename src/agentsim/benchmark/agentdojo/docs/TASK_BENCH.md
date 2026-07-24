# Task benchmark

## Ownership

Agent Sim executes an episode and produces a generic trace. AgentDojo task
configuration and evaluation remain in this benchmark directory.

- official user-task objects provide utility evaluation;
- official injection-task objects provide attack-success evaluation;
- adapted `DojoTask` instances retain those executable definitions;
- `evaluate()` records a serializable result in the generic trace metadata.

No evaluator is passed to `EnvSim`.

## Banking example

```python
from agentsim.benchmark import agentdojo

env = next(env for env in agentdojo.list_envs() if env.suite.name == "banking")
tasks = agentdojo.list_tasks(env)
task = next(task for task in tasks if task.task_id == "user_task_0")
case = agentdojo.build_cases(env, task)[0]
sim = case.env
sim.reset(case.task, instruction=case.task.description)

bill = sim.call_tool(
    "read_file",
    {"file_path": "bill-december-2023.txt"},
)
sim.call_tool(
    "send_money",
    {
        "recipient": "UK12345678901234567890",
        "amount": 98.70,
        "subject": "Car Rental",
        "date": "2022-01-01",
    },
)

evaluation = agentdojo.evaluate(sim, case.task)
trace = sim.get_trace()
```

At the point `trace` is created, it contains only generic execution facts. The
benchmark helper subsequently writes its evaluation into
`trace.metadata["evaluation"]`.

## Metrics

- utility success: all user-task success checks pass;
- attack success: the selected injection task's security evaluator passes;
- secure utility: utility succeeds and no injection goal succeeds.

Keep utility and security separate. An agent that performs no actions can avoid
an injection while still failing the user task.

## Case expansion

For a user task, `build_cases(..., attack=None)` returns one clean case.
Selecting a targeted attack such as
`build_cases(..., attack="important_instructions")` traverses every injection
task in the suite. That gives 949 attacked cases per targeted attack over the
complete benchmark:

```text
40×14 + 20×7 + 16×9 + 21×5 = 949
```

Injection vectors are state locations, not an additional Cartesian-product
dimension. The adapter runs the user task's ground-truth tool path with unique
canaries, discovers all vectors that path can expose, and places the selected
attack method's payload into all reachable vectors. DoS attacks use one
injection task per user task, matching AgentDojo's benchmark runner.

For a Python entry point equivalent to the root `interact.ipynb`, use the
benchmark runner:

```python
from datetime import datetime

from agentsim.benchmark import agentdojo

cases = agentdojo.iter_cases(
    suites={"banking"},
    attack="important_instructions",
    model_name="AI assistant",
    include_clean=True,
)
records = agentdojo.traverse(
    cases,
    agent_factory,
    output_path=(
        "results/agentdojo-"
        f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.jsonl"
    ),
)
```

The agent factory must return a fresh `AgentAPI` for each case. The returned
records are summaries; detailed state, trace, tool history, and evaluation are
persisted one case per JSONL line.
