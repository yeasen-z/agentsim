"""Vendor the data and task-suite subset of AgentDojo used by the adapter.

This is a maintainer tool, not a runtime dependency. It copies the upstream
suite definitions and fixtures, then rewrites their absolute imports into the
private ``agentsim.benchmark.agentdojo._vendor`` namespace.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

VENDOR_PACKAGE = "agentsim.benchmark.agentdojo._vendor"
ROOT_FILES = (
    "base_tasks.py",
    "functions_runtime.py",
    "strenum.py",
    "yaml_loader.py",
)


def copy_python(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")
    text = text.replace("agentdojo.", f"{VENDOR_PACKAGE}.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def copy_tree(source: Path, destination: Path, pattern: str) -> None:
    for path in sorted(source.rglob(pattern)):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(source)
        target = destination / relative
        if path.suffix == ".py":
            copy_python(path, target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    upstream_package = args.upstream.resolve() / "src" / "agentdojo"
    destination = args.destination.resolve()
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing vendor directory: {destination}")

    destination.mkdir(parents=True)
    (destination / "__init__.py").write_text(
        '"""Private AgentDojo v0.1.35 compatibility subset."""\n',
        encoding="utf-8",
    )

    for filename in ROOT_FILES:
        copy_python(upstream_package / filename, destination / filename)

    copy_python(
        upstream_package / "task_suite" / "task_combinators.py",
        destination / "task_suite" / "task_combinators.py",
    )
    copy_python(
        upstream_package / "task_suite" / "__init__.py",
        destination / "task_suite" / "__init__.py",
    )
    copy_python(
        upstream_package / "task_suite" / "load_suites.py",
        destination / "task_suite" / "load_suites.py",
    )
    copy_tree(
        upstream_package / "default_suites",
        destination / "default_suites",
        "*.py",
    )
    copy_tree(
        upstream_package / "data" / "suites",
        destination / "data" / "suites",
        "*",
    )


if __name__ == "__main__":
    main()
