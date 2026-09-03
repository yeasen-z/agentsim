# AgentSim development guide

## Design principles

- Code logic must be clear and easy to understand before it is made highly
  generic or highly configurable.
- Prefer simple, direct code that a new contributor can follow without
  reconstructing hidden control flow.
- Keep constants close to the behavior that owns them. Avoid duplicated names,
  string literals, and large constant tables when one clear source of truth is
  enough.
- Use precise names that communicate domain ownership; avoid vague modules such
  as `utils.py` or `common.py` when a more specific name is available.
- Keep responsibilities layered, but do not over-split the code. A directory
  or module should represent a meaningful boundary; do not create a package
  for a single small class unless it has an independent lifecycle or public
  API.
- Prefer a small number of cohesive modules over many thin forwarding files.
- Keep functions locally understandable. Extract a function when it gives a
  meaningful name to a domain operation, not merely to reduce line count.
- Design boundaries so implementations can be replaced or moved without
  rewriting unrelated layers. Depend on small protocols and data records at
  layer boundaries.
- Optimize for refactorability: avoid implicit global state, import-time side
  effects, hidden registries, and duplicated lifecycle logic.
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

## Changes

- When adding a module, first check whether the logic belongs in an existing
  cohesive module.
- Before adding a constant, check whether it is genuinely shared and stable;
  otherwise keep it local to the component that uses it.
- When moving a boundary, update imports, documentation, and examples in the
  same change.
- Keep public names and dependency direction obvious from the file tree.
- Prefer a small, readable breaking change over preserving an unclear legacy
  abstraction; destructive internal updates are allowed in this project.
- Remove generated caches and temporary test artifacts after local checks.
