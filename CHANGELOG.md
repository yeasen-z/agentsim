# Changelog

All notable changes to Agent Sim will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Adopted a standard `src` package layout.
- Consolidated packaging and development configuration in `pyproject.toml`.
- Removed generated caches and package metadata from version control.
- Declared the runtime dependency on PyYAML.
- Moved the bundled simulation environments into the installable
  `agent_sim.scenarios` package.

## [0.2.0] - 2026-07-19

### Added

- Deterministic state, tool execution, verification, and trace primitives.
- Pluggable scenario registry and environment adapter APIs.
- LLM simulation helpers and multi-agent orchestration primitives.
- Mobile-domain example scenarios and import tests.

[Unreleased]: https://github.com/yeasen-z/agent-sim/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/yeasen-z/agent-sim/releases/tag/v0.2.0
