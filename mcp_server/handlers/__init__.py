from importlib import import_module
from pkgutil import iter_modules
from pathlib import Path
from fastapi import APIRouter

routers = []

_package_dir = Path(__file__).parent
for mod in iter_modules([str(_package_dir)]):
    if mod.ispkg or mod.name == "__init__":
        continue
    module = import_module(f"{__name__}.{mod.name}")
    router = getattr(module, "router", None)
    if isinstance(router, APIRouter):
        routers.append(router)
