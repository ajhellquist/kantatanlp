"""Automatic tool registry."""
from importlib import import_module
from pkgutil import iter_modules
from pathlib import Path

schemas = []

_package_dir = Path(__file__).parent
for mod in iter_modules([str(_package_dir)]):
    if mod.ispkg:
        continue
    module = import_module(f"{__name__}.{mod.name}")
    if hasattr(module, "schema"):
        schemas.append(module.schema)
