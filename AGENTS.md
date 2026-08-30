# AgentSim development guide

## Design principles

- Code logic must be clear and easy to understand before it is made highly
  generic or highly configurable.
- Keep responsibilities layered, but do not over-split the code. A directory
  or module should represent a meaningful boundary; do not create a package
  for a single small class unless it has an independent lifecycle or public
  API.
- Prefer a small number of cohesive modules over many thin forwarding files.
- Keep the four ownership layers explicit:
  - `env` owns the authoritative environment state and tool execution.
  - `agent` owns each agent's private state and agent behavior.
  - `scaffold` owns single-/multi-agent coordination and scheduling.
  - `trace` records facts across the other layers without controlling them.
- `runtime` connects the layers for episode execution; it must not become a
  second owner of environment, agent, or scaffold state.
- Generic framework code must not depend on concrete benchmark packs. Concrete
  benchmarks live under `benchmarks/` and depend on `src/agentsim`.

## Repository layout

- `src/agentsim/` contains the installable framework package.
- `benchmarks/` contains concrete benchmark implementations, loaders, fixtures,
  and benchmark-specific evaluation logic.
- `tutorial/` contains teaching and integration examples, not framework code.

## Changes

- When adding a module, first check whether the logic belongs in an existing
  cohesive module.
- When moving a boundary, update imports, documentation, and tutorial examples in the
  same change.
- Keep public names and dependency direction obvious from the file tree.
- Remove generated caches and temporary test artifacts after local checks.
