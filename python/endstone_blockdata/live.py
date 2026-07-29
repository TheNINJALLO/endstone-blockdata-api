"""Typed Python adapter for the native ``endstone:blockdata:v2`` service."""

from __future__ import annotations

from copy import deepcopy
from importlib import import_module
from types import ModuleType
from typing import Any

from . import __version__

from .model import (
    ApplyResult,
    BlockEntitySnapshot,
    BlockLocation,
    BlockPatch,
    BlockSnapshot,
    ConflictPolicy,
    InventorySlotSnapshot,
)


def _missing_import_target(error: ModuleNotFoundError, target: str) -> bool:
    """Return true only when ``target`` (or one of its parents) is absent."""
    return bool(error.name) and (
        error.name == target or target.startswith(f"{error.name}.")
    )


def _load_live_bridge() -> ModuleType:
    errors: list[str] = []
    for module_name in (
        "endstone_blockdata_inspector._endstone_blockdata_live",
        "endstone_blockdata._endstone_blockdata_live",
        "_endstone_blockdata_live",
    ):
        try:
            bridge = import_module(module_name)
        except ModuleNotFoundError as error:
            if not _missing_import_target(error, module_name):
                # A present bridge with a missing dependency is broken. Do not
                # hide the loader/ABI error by importing a stale fallback.
                raise
            errors.append(f"{module_name}: {error}")
            continue

        bridge_version = getattr(bridge, "__version__", None)
        if bridge_version != __version__:
            raise RuntimeError(
                f"native BlockData bridge {module_name!r} has version "
                f"{bridge_version!r}; the Python API requires {__version__!r}"
            )
        return bridge

    raise ModuleNotFoundError(
        "the native BlockData live bridge is not installed; tried "
        + "; ".join(errors),
        name="_endstone_blockdata_live",
    )


def _snapshot_from_mapping(raw: dict[str, Any]) -> BlockSnapshot:
    location = raw.get("location")
    if not isinstance(location, dict):
        raise ValueError("live snapshot has no location mapping")
    block_location = BlockLocation(
        str(location.get("dimension", "")),
        int(location["x"]),
        int(location["y"]),
        int(location["z"]),
    )

    actor_raw = raw.get("block_entity")
    actor: BlockEntitySnapshot | None = None
    if actor_raw is not None:
        if not isinstance(actor_raw, dict):
            raise ValueError("live block_entity must be a mapping or None")
        inventory_raw = actor_raw.get("inventory", [])
        if not isinstance(inventory_raw, list):
            raise ValueError("live block-entity inventory must be a list")
        inventory: list[InventorySlotSnapshot] = []
        for entry in inventory_raw:
            if not isinstance(entry, dict) or not isinstance(entry.get("item"), dict):
                raise ValueError("live inventory entry is malformed")
            inventory.append(
                InventorySlotSnapshot(
                    int(entry["slot"]),
                    deepcopy(entry["item"]),
                    int(entry.get("revision", 0)),
                )
            )
        nbt = actor_raw.get("nbt", {})
        if not isinstance(nbt, dict):
            raise ValueError("live block-entity NBT must be a compound mapping")
        actor = BlockEntitySnapshot(
            type=str(actor_raw.get("type", "")),
            nbt=deepcopy(nbt),
            raw_snbt=str(actor_raw.get("snbt", "")),
            canonical_nbt=bool(actor_raw.get("canonical", False)),
            inventory=inventory,
            is_container=bool(actor_raw.get("is_container", False)),
            container_size=int(actor_raw.get("container_size", 0)),
        )

    states = raw.get("states", {})
    if not isinstance(states, dict):
        raise ValueError("live block states must be a mapping")
    return BlockSnapshot(
        location=block_location,
        type=str(raw.get("type", "minecraft:air")),
        runtime_id=int(raw.get("runtime_id", 0)),
        states=deepcopy(states),
        block_entity=actor,
        revision=int(raw.get("revision", 0)),
        block_entity_status=str(raw.get("block_entity_status", "not_supported")),
    )


def _patch_to_mapping(patch: BlockPatch) -> dict[str, Any]:
    return {
        "location": {
            "dimension": patch.location.dimension,
            "x": patch.location.x,
            "y": patch.location.y,
            "z": patch.location.z,
        },
        "expected_revision": patch.expected_revision,
        "replacement_type": patch.replacement_type,
        "state_updates": deepcopy(patch.state_updates),
        "state_removals": sorted(patch.state_removals),
        "nbt_updates": deepcopy(patch.nbt_updates),
        "nbt_removals": sorted(patch.nbt_removals),
        "inventory_updates": deepcopy(patch.inventory_updates),
        "inventory_removals": sorted(patch.inventory_removals),
    }


def _policy_name(policy: ConflictPolicy) -> str:
    names = {
        ConflictPolicy.FAIL_IF_CHANGED: "fail_if_changed",
        ConflictPolicy.MERGE_CHANGED_PATHS: "merge_changed_paths",
        ConflictPolicy.MERGE_INVENTORY_SLOTS: "merge_inventory_slots",
        ConflictPolicy.REPLACE: "replace",
        ConflictPolicy.FORCE: "force",
    }
    try:
        return names[policy]
    except (KeyError, TypeError) as error:
        raise ValueError("unknown BlockData conflict policy") from error


class LiveBlockDataAdapter:
    """Adapter consumed by :class:`BlockDataService` for live server access.

    Endstone calls must run on its primary thread. The native bridge enforces
    that boundary and this wrapper converts bridge mappings to the typed public
    Python model.
    """

    def __init__(self, server: Any, bridge: Any | None = None) -> None:
        self.server = server
        self.bridge = bridge if bridge is not None else _load_live_bridge()

    @property
    def available(self) -> bool:
        return bool(self.bridge.available(self.server))

    def capabilities(self) -> dict[str, Any]:
        return dict(self.bridge.capabilities(self.server))

    def capture(self, location: BlockLocation) -> BlockSnapshot | None:
        raw = self.bridge.capture(
            self.server,
            location.dimension,
            location.x,
            location.y,
            location.z,
        )
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raw = dict(raw)
        return _snapshot_from_mapping(raw)

    def capture_region(
        self,
        dimension: str,
        minimum: tuple[int, int, int],
        maximum: tuple[int, int, int],
    ) -> list[BlockSnapshot]:
        raw_snapshots = self.bridge.capture_region(
            self.server,
            dimension,
            *minimum,
            *maximum,
        )
        snapshots: list[BlockSnapshot] = []
        for raw in raw_snapshots:
            if not isinstance(raw, dict):
                raw = dict(raw)
            snapshots.append(_snapshot_from_mapping(raw))
        return snapshots

    def apply(self, patch: BlockPatch, policy: ConflictPolicy) -> ApplyResult:
        raw = dict(
            self.bridge.apply(
                self.server,
                _patch_to_mapping(patch),
                _policy_name(policy),
            )
        )
        return ApplyResult(
            bool(raw.get("ok", False)),
            str(raw.get("status", "adapter_error")),
            str(raw.get("message", "live adapter returned no message")),
            int(raw.get("resulting_revision", 0)),
        )
