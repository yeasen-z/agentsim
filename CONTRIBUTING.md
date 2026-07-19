# Contributing

Thank you for contributing to Agent Sim.

## Development setup

```bash
git clone https://github.com/yeasen-z/agent-sim.git
cd agent-sim
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

On Windows, activate the environment with `.venv\\Scripts\\activate`.

## Before opening a pull request

Run the project checks from the repository root:

```bash
ruff check .
black --check .
pytest
python -m build
```

Keep changes focused, add tests for behavior changes, and update the README or
changelog when a public API or user-facing behavior changes.

## Pull requests

Describe the problem, the chosen approach, and how the change was verified.
Avoid committing virtual environments, caches, build artifacts, credentials,
or local editor configuration.
