""" Implements a loader for Python scripts. These Python scripts have access to importing certain build context
related members from the :mod:`kraken.api` module; note that these members are only available when imported in
the context of a script executed by this loader and not otherwise. """

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

from kraken.core.project import Project

from . import BuildScriptLoader

DEFAULT_FILE = Path("kraken.py")


class PyscriptLoader(BuildScriptLoader):
    def detect_in_project_directory(self, project_dir: Path) -> Path | None:
        file = project_dir / DEFAULT_FILE
        return file if file.is_file() else None

    def match_file(self, file: Path) -> bool | Path | None:
        return file.suffix == ".py"

    def load_script(self, file: Path, project: Project) -> None:
        api_module_name = "kraken.api"

        # Create the temporary replacement for the kraken.api module that the script will import from.
        api_module: Any = types.ModuleType(api_module_name)
        api_module.ctx = project.context
        api_module.project = project

        # In order for @dataclass decorators to work in a Python script loaded by this build, it must be
        # able to look up the module in sys.modules.
        module = types.ModuleType(f"_kraken__{project.name}_{id(project)}")
        module.__file__ = str(file)

        old_module = sys.modules.get(api_module_name)
        try:
            sys.modules[api_module_name] = api_module
            sys.modules[module.__name__] = module
            code = compile(file.read_text(), filename=file, mode="exec")
            exec(code, vars(module))
        finally:
            del sys.modules[module.__name__]
            if old_module is None:
                sys.modules.pop(api_module_name)
            else:
                sys.modules[api_module_name] = old_module