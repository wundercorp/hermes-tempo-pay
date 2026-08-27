from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
HERMES_REPO = Path(os.environ.get("HERMES_REPO", "/mnt/data/hermes_full"))

if str(HERMES_REPO) not in sys.path:
    sys.path.insert(0, str(HERMES_REPO))

if "hermes_tempo_payments" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "hermes_tempo_payments",
        PLUGIN_ROOT / "__init__.py",
        submodule_search_locations=[str(PLUGIN_ROOT)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load plugin package from {PLUGIN_ROOT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["hermes_tempo_payments"] = module
    spec.loader.exec_module(module)
