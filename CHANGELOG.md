# Changelog

All notable changes to Agent Sim will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Replaced the duplicate long-form interface APIs with the compact
  `Env`, `AgentAPI`, `RuntimeAPI`, `EnvInfo`, and `EnvAdapter` API.
- Separated benchmark evaluation from `EnvSim`; the sim now
  owns execution and generic tracing only.
- Moved concrete toy scenarios from the installable framework package to
  `examples/scenarios`.
- Added the complete AgentDojo v1.2.2 benchmark under
  `agentsim.benchmark.agentdojo`: four environments, 97 user tasks, 35
  injection tasks, original tools/evaluators, and all versioned fixtures.
- Added AgentDojo's 17 registered attack methods and explicit per-run attack
  selection. Targeted attacks traverse all 949 user-task/injection-task pairs;
  DoS attacks use one injection target per user task, matching AgentDojo.
- Attack payloads are injected into state vectors found through AgentDojo's
  canary reachability procedure, and case IDs record the selected method.
- Added a reusable AgentDojo `run_case()` / `iter_cases()` / `traverse()` API
  for application `main.py` entry points, including per-case JSONL output.
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
