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
from agentsim import LLMAdapter, SingleAgentScaffold
import benchmarks.agentdojo as agentdojo

env = next(env for env in agentdojo.list_envs() if env.suite.name == "banking")
tasks = agentdojo.list_tasks(env)
task = next(task for task in tasks if task.task_id == "user_task_0")
suite_name, task = next(agentdojo.tasks.iter_tasks(
    suites={env.suite.name}, user_task_ids={task.task_id}
))
sim = agentdojo.benchmark.create_env(case)
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

For a user task, `iter_tasks(..., attack=None)` yields one clean task.
Selecting a targeted attack such as
`iter_tasks(..., attack="important_instructions")` traverses every injection
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

from agentsim import LLMAdapter, SingleAgentScaffold
import benchmarks.agentdojo as agentdojo

tasks = agentdojo.iter_suite_tasks(
    suites={"banking"},
    attack="important_instructions",
    model_name="AI assistant",
    include_clean=True,
)
records = agentdojo.traverse(
    cases,
    lambda: SingleAgentScaffold(
        LLMAdapter(YourLLMClient(), agent_id="assistant"),
        max_turns=30,
    ),
    output_path=(
        "results/agentdojo-"
        f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}.jsonl"
    ),
)
```

The scaffold factory must return a fresh `ScaffoldAPI` for each case. The
returned records are summaries; detailed state, trace, action/tool history, and
evaluation are persisted one case per JSONL line.
