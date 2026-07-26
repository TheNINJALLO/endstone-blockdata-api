"""Compatibility import for running the inspector from a source checkout.

The wheel packages the canonical implementation under ``src/``. Keeping this
shim avoids a second, divergent command definition in the example directory.
"""

from pathlib import Path
import sys

_SOURCE_DIRECTORY = Path(__file__).resolve().parent / "src"
if str(_SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(_SOURCE_DIRECTORY))

from endstone_blockdata_inspector import BlockDataInspectorPlugin

__all__ = ["BlockDataInspectorPlugin"]
