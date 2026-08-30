# Changelog

All notable changes to Agent Sim will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Renamed the environment state API from `HiddenState` / `hidden_state` to
  `EnvState` / `env_state` as a breaking change.
- Rebuilt episode ownership around four explicit layers: `EnvState`, per-agent
  `AgentState`, scaffold-owned orchestration state, and append-only `Trace`.
- Replaced tuple-based agent decisions with actor-attributed structured
  `Action` records and added one `EpisodeRuntime` for single- and multi-agent
  scaffolds.
- Added common `BenchmarkAdapter`, `EvaluationResult`,
  `BenchmarkRegistry`, and traversal contracts so multiple benchmark packs use
  the same execution path.
- Replaced the duplicate long-form interface APIs with the compact
  `Env`, `AgentAPI`, `ScaffoldAPI`, `RuntimeAPI`, `EnvInfo`, and `EnvAdapter` API.
- Separated benchmark evaluation from `EnvSim`; the sim now
  owns execution and generic tracing only.
- Moved concrete toy scenarios from the installable framework package to
  `tutorial/scenarios`.
- Added the complete AgentDojo v1.2.2 benchmark under
  `benchmarks.agentdojo`: four environments, 97 user tasks, 35
  injection tasks, original tools/evaluators, and all versioned fixtures.
- Added AgentDojo's 17 registered attack methods and explicit per-run attack
  selection. Targeted attacks traverse all 949 user-task/injection-task pairs;
  DoS attacks use one injection target per user task, matching AgentDojo.
- Attack payloads are injected into state vectors found through AgentDojo's
  canary reachability procedure, and case IDs record the selected method.
- Added reusable AgentDojo suite task loading and `run_task()` / `traverse()` APIs
  for application `main.py` entry points, including per-case JSONL output.
- Redesigned benchmark adapters so each suite directly owns an `Env` and tasks are
  loaded as `(suite_name, TaskDefine)` pairs.
  descriptor and `BenchmarkAdapter.create_env()` constructs the fresh
  `EnvSim`; mutable environment state no longer lives inside a case.
- Removed repository-local test fixtures and test-only CI configuration; the
  installable package now ships only runtime, benchmark, example, and
  documentation assets.
- Adopted a standard `src` package layout.
- Consolidated packaging and development configuration in `pyproject.toml`.
- Removed generated caches and package metadata from version control.
- Declared the runtime dependencies required by the pinned AgentDojo data and
  raised the minimum Python version to 3.10.

## [0.2.0] - 2026-07-19

### Added

- Deterministic state, tool execution, verification, and trace primitives.
- Pluggable scenario registry and environment adapter APIs.
- LLM simulation helpers and multi-agent orchestration primitives.
- Mobile-domain example scenarios and import tests.

[Unreleased]: https://github.com/yeasen-z/agent-sim/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/yeasen-z/agent-sim/releases/tag/v0.2.0
