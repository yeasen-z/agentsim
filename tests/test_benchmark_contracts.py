import json

import benchmarks.agentdojo as agentdojo
import benchmarks.agentdyn as agentdyn
import benchmarks.injecagent as injecagent
from agentsim import LLMAdapter, MockLLMClient, SingleAgentScaffold, TaskDefine
from benchmarks.common import (
    BenchmarkCase,
    CampaignSpec,
    CaseSelection,
    CaseVariant,
    JsonlResultStore,
    NativeBenchmarkPack,
    Provenance,
    SuiteInfo,
    VariantKind,
    run_campaign,
    run_case,
    traverse,
    validate_pack,
)


def test_common_case_records_are_json_serializable():
    provenance = Provenance(
        source_url="https://example.test/benchmark",
        source_revision="deadbeef",
        source_version="v1",
        license_id="MIT",
    )
    suite = SuiteInfo("mail", "Mail")
    selection = CaseSelection(
        suites={"mail"},
        task_ids={"task-1"},
        variants={"clean"},
    )
    case = BenchmarkCase(
        case_id="example/mail/task-1/clean",
        benchmark_id="example",
        suite_id=suite.suite_id,
        task=TaskDefine(task_id="task-1", scenario="mail"),
        variant=CaseVariant("clean", VariantKind.CLEAN),
        payload=object(),
    )

    json.dumps(provenance.to_dict())
    json.dumps(suite.to_dict())
    json.dumps(selection.to_dict())
    serialized = case.to_dict()
    json.dumps(serialized)

    assert "payload" not in serialized
    assert selection.suites == frozenset({"mail"})
    assert selection.variants == frozenset({VariantKind.CLEAN})


def test_clean_variant_rejects_attack_identity():
    try:
        CaseVariant("invalid", VariantKind.CLEAN, attack_id="attack")
    except ValueError as error:
        assert "Clean variants" in str(error)
    else:
        raise AssertionError("Clean variants must reject attack metadata")


def test_three_benchmark_inventories_are_frozen():
    dojo_envs = agentdojo.list_envs()
    dyn_envs = agentdyn.list_envs()
    injec_env = injecagent.list_envs()[0]

    assert [(env.suite.name, len(agentdojo.list_tasks(env))) for env in dojo_envs] == [
        ("workspace", 40),
        ("travel", 20),
        ("banking", 16),
        ("slack", 21),
    ]
    assert sum(len(env.suite.injection_tasks) for env in dojo_envs) == 35
    assert len(agentdojo.list_attacks()) == 17

    assert [(env.suite.name, len(agentdyn.list_tasks(env))) for env in dyn_envs] == [
        ("shopping", 20),
        ("github", 20),
        ("dailylife", 20),
    ]
    assert sum(len(env.suite.injection_tasks) for env in dyn_envs) == 28
    assert (
        sum(task.ground_truth_valid for env in dyn_envs for task in env.suite.user_tasks.values())
        == 45
    )

    assert len(injec_env.data.dh_cases) == 510
    assert len(injec_env.data.ds_cases) == 544
    assert len(injec_env.data.tools) == 330
    assert len(injec_env.data.attacker_responses) == 1384


def test_agentdojo_native_pack_enumerates_stable_cases():
    pack = agentdojo.benchmark
    selection = CaseSelection(variants={VariantKind.CLEAN})

    first_pass = list(pack.iter_cases(selection))
    second_pass = list(pack.iter_cases(selection))

    assert isinstance(pack, NativeBenchmarkPack)
    assert len(first_pass) == 97
    assert [case.case_id for case in first_pass] == [case.case_id for case in second_pass]
    assert first_pass[0].case_id == "agentdojo/workspace/user_task_0/clean"
    assert len(pack.suites()) == 4
    assert pack.info().provenance is not None
    assert len(list(pack.iter_cases())) == 97


def test_agentdojo_native_attack_selection_and_shared_runner():
    pack = agentdojo.benchmark
    attacked = list(
        pack.iter_cases(
            CaseSelection(
                suites={"workspace"},
                task_ids={"user_task_0"},
                variants={VariantKind.ATTACKED},
                attack_ids={"direct"},
                injection_task_ids={"injection_task_0"},
            )
        )
    )
    assert [case.case_id for case in attacked] == [
        "agentdojo/workspace/user_task_0/direct/injection_task_0"
    ]

    clean = next(
        iter(
            pack.iter_cases(
                CaseSelection(
                    suites={"workspace"},
                    task_ids={"user_task_0"},
                    variants={VariantKind.CLEAN},
                )
            )
        )
    )
    scaffold = SingleAgentScaffold(
        LLMAdapter(MockLLMClient(['{"action_type":"return","output":"done"}']))
    )
    result = run_case(pack, clean, scaffold)

    assert result.case is clean
    assert result.evaluation.case_id == clean.case_id
    assert result.to_dict()["variant"]["kind"] == "clean"
    assert result.execution.trace.metadata["benchmark"]["case"]["case_id"] == clean.case_id


def test_injecagent_native_pack_preserves_precomposed_cases():
    pack = injecagent.benchmark
    cases = list(pack.iter_cases())

    assert isinstance(pack, NativeBenchmarkPack)
    assert len(cases) == 1054
    assert sum(case.variant.attack_id == "dh" for case in cases) == 510
    assert sum(case.variant.attack_id == "ds" for case in cases) == 544
    assert {case.variant.kind for case in cases} == {VariantKind.ATTACKED}
    assert len({case.case_id for case in cases}) == 1054
    assert pack.info().provenance is not None


def test_injecagent_noop_is_not_reported_as_a_pass():
    pack = injecagent.benchmark
    case = next(iter(pack.iter_cases(CaseSelection(task_ids={"dh_0"}))))
    scaffold = SingleAgentScaffold(
        LLMAdapter(MockLLMClient(['{"action_type":"return","output":"done"}']))
    )

    result = run_case(pack, case, scaffold)

    assert result.evaluation.passed is None
    assert result.evaluation.metrics["attack_success"] is False
    assert result.evaluation.metrics["utility_success"] is None


def test_campaign_jsonl_resume_uses_stable_run_ids(tmp_path):
    store = JsonlResultStore(tmp_path / "campaign")
    spec = CampaignSpec(
        campaign_id="injecagent-smoke",
        selection=CaseSelection(task_ids={"dh_0", "dh_1"}),
        max_scaffold_turns=2,
    )

    def scaffold_factory():
        return SingleAgentScaffold(
            LLMAdapter(MockLLMClient(['{"action_type":"return","output":"done"}']))
        )

    first = run_campaign(injecagent.benchmark, scaffold_factory, spec, store)
    second = run_campaign(injecagent.benchmark, scaffold_factory, spec, store)
    records = [
        json.loads(line) for line in store.records_path.read_text(encoding="utf-8").splitlines()
    ]

    assert first.executed_runs == 2
    assert first.error_runs == 0
    assert second.executed_runs == 0
    assert second.skipped_runs == 2
    assert len(records) == 2
    assert len({record["run_id"] for record in records}) == 2


def test_campaign_retries_error_records_without_repeating_completed_runs(tmp_path):
    class FailingPack:
        def __init__(self, delegate):
            self.delegate = delegate

        def info(self):
            return self.delegate.info()

        def suites(self):
            return self.delegate.suites()

        def iter_cases(self, selection=None):
            return self.delegate.iter_cases(selection)

        def create_env(self, case):
            if case.task.task_id == "dh_0":
                raise RuntimeError("injected construction failure")
            return self.delegate.create_env(case)

        def evaluate(self, env, case, run):
            return self.delegate.evaluate(env, case, run)

    store = JsonlResultStore(tmp_path / "retry")
    spec = CampaignSpec(
        campaign_id="injecagent-retry",
        selection=CaseSelection(task_ids={"dh_0", "dh_1"}),
        max_scaffold_turns=2,
    )
    pack = FailingPack(injecagent.benchmark)

    def scaffold_factory():
        return SingleAgentScaffold(
            LLMAdapter(MockLLMClient(['{"action_type":"return","output":"done"}']))
        )

    first = run_campaign(pack, scaffold_factory, spec, store)
    second = run_campaign(pack, scaffold_factory, spec, store)
    records = [json.loads(line) for line in store.records_path.read_text().splitlines()]

    assert first.error_runs == 1
    assert first.executed_runs == 2
    assert second.error_runs == 1
    assert second.executed_runs == 1
    assert second.skipped_runs == 1
    assert len(records) == 3
    assert [record["status"] for record in records].count("error") == 2


def test_agentdyn_native_pack_preserves_clean_and_official_attack_inventory():
    pack = agentdyn.benchmark
    clean = list(pack.iter_cases(CaseSelection(variants={VariantKind.CLEAN})))
    attacked = list(pack.iter_cases(CaseSelection(variants={VariantKind.ATTACKED})))

    assert isinstance(pack, NativeBenchmarkPack)
    assert len(clean) == 60
    assert sum(case.metadata["ground_truth_valid"] for case in clean) == 45
    assert len(attacked) == 560
    assert len({case.case_id for case in [*clean, *attacked]}) == 620
    assert pack.info().provenance is not None
    assert len(list(pack.iter_cases())) == 60


def test_same_shared_runner_executes_all_three_native_packs():
    selections = (
        (
            agentdojo.benchmark,
            CaseSelection(
                suites={"banking"},
                task_ids={"user_task_0"},
                variants={VariantKind.CLEAN},
            ),
        ),
        (injecagent.benchmark, CaseSelection(task_ids={"dh_0"})),
        (
            agentdyn.benchmark,
            CaseSelection(
                suites={"shopping"},
                task_ids={"user_task_0"},
                variants={VariantKind.CLEAN},
            ),
        ),
    )

    for pack, selection in selections:
        case = next(iter(pack.iter_cases(selection)))
        scaffold = SingleAgentScaffold(
            LLMAdapter(MockLLMClient(['{"action_type":"return","output":"done"}']))
        )
        result = run_case(pack, case, scaffold)
        assert result.case is case
        assert result.evaluation.case_id == case.case_id


def test_generic_pack_conformance_reports_all_three_native_packs():
    for pack in (agentdojo.benchmark, injecagent.benchmark, agentdyn.benchmark):
        report = validate_pack(pack)
        assert report.passed, report.to_dict()
        assert report.checks["case_ids_unique"] is True
        assert report.checks["case_ids_stable"] is True
        json.dumps(report.to_dict())


def test_legacy_traverse_wrapper_uses_cases_and_keeps_jsonl_fields(tmp_path):
    pack = agentdojo.benchmark
    cases = pack.iter_cases(
        CaseSelection(
            suites={"banking"},
            task_ids={"user_task_0"},
            variants={VariantKind.CLEAN},
        )
    )
    output = tmp_path / "legacy.jsonl"
    summaries = traverse(
        pack,
        cases,
        lambda: SingleAgentScaffold(
            LLMAdapter(MockLLMClient(['{"action_type":"return","output":"done"}']))
        ),
        output_path=output,
        max_tasks=1,
    )
    record = json.loads(output.read_text(encoding="utf-8"))

    assert summaries[0]["case_id"] == "agentdojo/banking/user_task_0/clean"
    assert summaries[0]["task_id"] == "user_task_0"
    assert record["details"]["case_id"] == summaries[0]["case_id"]
