"""
Agent Sim - Scenario Registry

Pluggable architecture for custom simulation environments.
Scenarios can be registered via decorators, config files, or auto-discovery.
"""

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml


@dataclass
class Plugin:
    """Metadata for a registered scenario plugin."""

    id: str
    name: str
    description: str
    module: str
    version: str = "1.0.0"
    author: str = ""

    # Callables provided by the plugin (internal names)
    init_state: Optional[Callable] = None
    register_tools: Optional[Callable] = None
    compile_observation: Optional[Callable] = None

    # Additional metadata
    tags: List[str] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "module": self.module,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "config": self.config,
        }


class Registry:
    """
    Central registry for all available scenarios.

    Supports:
    - Programmatic registration via register()
    - Decorator-based registration via @register
    - File-based loading from YAML configs
    - Module discovery from directories
    """

    _instance: Optional["Registry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._plugins: Dict[str, Plugin] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(
        self,
        id: str,
        name: str,
        description: str,
        module: str,
        init_state: Callable,
        register_tools: Callable,
        compile_observation: Optional[Callable] = None,
        version: str = "1.0.0",
        author: str = "",
        tags: List[str] = None,
        config: Dict[str, Any] = None,
    ) -> Plugin:
        """
        Register a scenario plugin programmatically.

        Args:
            id: Unique identifier for the scenario
            name: Human-readable name
            description: Scenario description
            module: Python module path containing the implementation
            init_state: Function to initialize environment state
            register_tools: Function to register tools with ToolExecutor
            compile_observation: Optional function to compile observations
            version: Plugin version
            author: Plugin author
            tags: List of tags for categorization
            config: Additional configuration parameters

        Returns:
            Registered Plugin instance
        """
        plugin = Plugin(
            id=id,
            name=name,
            description=description,
            module=module,
            version=version,
            author=author,
            init_state=init_state,
            register_tools=register_tools,
            compile_observation=compile_observation,
            tags=tags or [],
            config=config or {},
        )

        self._plugins[id] = plugin

        # Add to categories based on tags
        for tag in plugin.tags:
            if tag not in self._categories:
                self._categories[tag] = []
            if id not in self._categories[tag]:
                self._categories[tag].append(id)

        return plugin

    def register_scenario(
        self,
        id: str,
        name: str = None,
        description: str = "",
        version: str = "1.0.0",
        author: str = "",
        tags: List[str] = None,
    ):
        """
        Decorator for registering scenarios.

        Usage:
            @registry.register_scenario(
                id="email_management",
                name="Email Management",
                tags=["productivity", "communication"]
            )
            def email_scenario():
                # Returns (init_state, register_tools, compile_observation)
                return init_state, register_tools, compile_observation
        """

        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs) -> tuple:
                result = func(*args, **kwargs)

                # Unpack results
                if len(result) == 2:
                    init_s, reg_t = result
                    compile_o = None
                elif len(result) == 3:
                    init_s, reg_t, compile_o = result
                else:
                    raise ValueError(
                        "Scenario function must return "
                        "(init_state, register_tools[, compile_observation])"
                    )

                # Register the scenario
                self.register(
                    id=id,
                    name=name or id.replace("_", " ").title(),
                    description=description,
                    module=func.__module__,
                    init_state=init_s,
                    register_tools=reg_t,
                    compile_observation=compile_o,
                    version=version,
                    author=author,
                    tags=tags,
                )

                return result

            return wrapper

        return decorator

    def get(self, id: str) -> Optional[Plugin]:
        """Get a scenario plugin by ID."""
        return self._plugins.get(id)

    def list(self, category: str = None) -> List[str]:
        """List all registered scenario IDs, optionally filtered by category."""
        if category:
            return self._categories.get(category, [])
        return list(self._plugins.keys())

    def list_scenarios(self, category: str = None) -> List[str]:
        """Alias for list() - List all registered scenario IDs."""
        return self.list(category)

    def all(self) -> Dict[str, Plugin]:
        """Get all registered scenarios."""
        return self._plugins.copy()

    def has(self, id: str) -> bool:
        """Check if a scenario is registered."""
        return id in self._plugins

    def load_yaml(self, path: str, base_module: str = ""):
        """
        Load scenario definitions from a YAML file.

        YAML format:
            scenarios:
              - id: email_management
                name: Email Management
                module: scenarios.email
                entrypoint: setup
                tags: [productivity, communication]
        """
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        for scenario_def in data.get("scenarios", []):
            module_name = scenario_def.get("module", "")
            if base_module and module_name:
                module_name = f"{base_module}.{module_name}"

            # Import the module
            module = importlib.import_module(module_name)

            # Get the entrypoint function
            entrypoint_name = scenario_def.get("entrypoint", "setup")
            entrypoint_func = getattr(module, entrypoint_name, None)

            if not entrypoint_func:
                raise ImportError(f"Module {module_name} has no '{entrypoint_name}' function")

            # Call the entrypoint to get components
            result = entrypoint_func()

            # Register the scenario
            if len(result) >= 2:
                self.register(
                    id=scenario_def["id"],
                    name=scenario_def.get("name", scenario_def["id"]),
                    description=scenario_def.get("description", ""),
                    module=module_name,
                    init_state=result[0],
                    register_tools=result[1],
                    compile_observation=result[2] if len(result) > 2 else None,
                    version=scenario_def.get("version", "1.0.0"),
                    author=scenario_def.get("author", ""),
                    tags=scenario_def.get("tags", []),
                )

    def discover(self, directory: str, package_prefix: str = ""):
        """
        Automatically discover and load scenarios from a directory.

        Looks for:
        - __init__.py files with register_scenarios(registry) function
        - Individual scenario modules with setup() function
        - scenario.yaml configuration files

        Args:
            directory: Path to the scenarios directory
            package_prefix: Python package prefix for imports
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        # Check for __init__.py with register_scenarios
        init_file = dir_path / "__init__.py"
        if init_file.exists():
            module_name = f"{package_prefix}.{dir_path.name}" if package_prefix else dir_path.name
            try:
                module = importlib.import_module(module_name)
                register_func = getattr(module, "register_scenarios", None)
                if register_func:
                    register_func(self)
            except ImportError as e:
                print(f"Warning: Could not import {module_name}: {e}")

        # Look for individual scenario modules
        for py_file in dir_path.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            module_name = (
                f"{package_prefix}.{dir_path.name}.{py_file.stem}"
                if package_prefix
                else f"{dir_path.name}.{py_file.stem}"
            )

            try:
                module = importlib.import_module(module_name)

                # Check for setup() function
                setup_func = getattr(module, "setup", None)
                if setup_func:
                    result = setup_func()
                    if result and len(result) >= 2:
                        # Extract scenario_id from module if possible
                        sid = getattr(module, "SCENARIO_ID", py_file.stem)
                        name = getattr(module, "SCENARIO_NAME", sid)
                        description = getattr(module, "SCENARIO_DESCRIPTION", "")
                        tags = getattr(module, "SCENARIO_TAGS", [])

                        self.register(
                            id=sid,
                            name=name,
                            description=description,
                            module=module_name,
                            init_state=result[0],
                            register_tools=result[1],
                            compile_observation=result[2] if len(result) > 2 else None,
                            tags=tags,
                        )
            except ImportError as e:
                print(f"Warning: Could not import {module_name}: {e}")

        # Look for scenario.yaml files
        for yaml_file in dir_path.glob("scenario.yaml"):
            self.load_yaml(str(yaml_file), base_module=package_prefix)

    def remove(self, id: str):
        """Remove a scenario from the registry."""
        if id in self._plugins:
            plugin = self._plugins[id]
            # Remove from categories
            for tag in plugin.tags:
                if tag in self._categories:
                    self._categories[tag].remove(id)
            del self._plugins[id]

    def clear(self):
        """Clear all registered scenarios."""
        self._plugins.clear()
        self._categories.clear()

    def get_categories(self) -> List[str]:
        """Get all available categories."""
        return list(self._categories.keys())


# Global registry instance
registry = Registry()


def get_registry() -> Registry:
    """Get the global scenario registry."""
    return registry


def register(
    id: str,
    name: str = None,
    description: str = "",
    version: str = "1.0.0",
    author: str = "",
    tags: List[str] = None,
):
    """
    Convenience function to register a scenario using decorator syntax.

    Usage:
        @register("my_scenario", tags=["custom"])
        def my_scenario_setup():
            return init_state, register_tools
    """
    return registry.register_scenario(
        id=id, name=name, description=description, version=version, author=author, tags=tags
    )
