# Benchmarks

This directory contains concrete benchmark implementations and their fixtures.
They are kept outside `src/agentsim` so the framework package remains focused on
the shared environment, agent, scaffold, trace, runtime, and benchmark-runner
contracts.

All three native packs use the same case and execution API. The compact default
selection returns clean cases for AgentDojo and AgentDyn; InjecAgent has no
upstream clean cases, so it returns its pre-composed attack cases.

```python
from agentsim import LLMAdapter, SingleAgentScaffold
from benchmarks.agentdojo import benchmark
from benchmarks.common import CaseSelection, VariantKind, run_case

case = next(
    iter(
        benchmark.iter_cases(
            CaseSelection(
                suites={"banking"},
                variants={VariantKind.CLEAN},
            )
        )
    )
)
scaffold = SingleAgentScaffold(LLMAdapter(your_llm_client))
result = run_case(benchmark, case, scaffold)
print(result.case.case_id, result.evaluation.to_dict())
```

Use `VariantKind.ATTACKED` with `attack_ids` and `injection_task_ids` to select
attack cases. The same calls work with `benchmarks.agentdyn.benchmark` and
`benchmarks.injecagent.benchmark`.

For multi-case research runs, use the serial campaign runner. It writes a
manifest and append-only JSONL records, and skips run IDs already in the store
when resumed:

```python
from benchmarks.common import CampaignSpec, JsonlResultStore, run_campaign

summary = run_campaign(
    benchmark,
    scaffold_factory=lambda: SingleAgentScaffold(LLMAdapter(your_llm_client)),
    spec=CampaignSpec(
        campaign_id="banking-clean",
        selection=CaseSelection(
            suites={"banking"},
            variants={VariantKind.CLEAN},
        ),
        seeds=(42,),
    ),
    store=JsonlResultStore("runs/banking-clean"),
)
```

`validate_pack(benchmark)` returns a JSON serializable conformance report for
case identity, stable enumeration, suite references, and record serialization.
Benchmark-specific validation modules exercise ground-truth tool calls and
evaluation semantics. Run them with:

```bash
python -m benchmarks.agentdojo.validation
python -m benchmarks.injecagent.validation
python -m benchmarks.agentdyn.validation
```
