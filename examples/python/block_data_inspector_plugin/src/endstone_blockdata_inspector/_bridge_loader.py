"""Import the native bridge from supported BlockData wheel layouts."""

from __future__ import annotations

import importlib
from types import ModuleType


BRIDGE_MODULE = "_endstone_blockdata_live"
BUNDLED_BRIDGE_MODULE = f"{__package__}.{BRIDGE_MODULE}"


def _missing_target(error: ModuleNotFoundError, target: str) -> bool:
    """Distinguish an absent bridge from an error inside a present bridge."""
    return error.name == target


def import_live_bridge(expected_version: str) -> ModuleType:
    """Import the bridge bundled inside the matching platform wheel."""
    try:
        bridge = importlib.import_module(BUNDLED_BRIDGE_MODULE)
    except ModuleNotFoundError as error:
        if not _missing_target(error, BUNDLED_BRIDGE_MODULE):
            raise
        raise ModuleNotFoundError(
            f"BlockData's package-local native bridge is not installed. Install the matching "
            f"{expected_version} CPython 3.14 platform wheel for this operating system; "
            "the portable py3-none-any command wheel does not contain the native bridge.",
            name=BUNDLED_BRIDGE_MODULE,
        ) from error
    bridge_version = getattr(bridge, "__version__", None)
    if bridge_version != expected_version:
        raise RuntimeError(
            f"BlockData's package-local native bridge has version "
            f"{bridge_version!r}; the command wheel requires {expected_version!r}. "
            "Remove older BlockData wheels and install the matching platform wheel."
        )
    return bridge
