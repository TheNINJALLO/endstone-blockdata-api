"""Live player-inventory snapshots and bundle-aware patch helpers."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from importlib import import_module
from typing import Any, Iterable, Mapping

from .storage_item import StorageItemRules, StorageItemView, is_storage_item_nbt

ItemNbt = dict[str, Any]


class PlayerInventorySection(str, Enum):
    MAIN = "main"
    ARMOR = "armor"
    OFFHAND = "offhand"
    ENDER_CHEST = "ender_chest"


@dataclass(frozen=True, slots=True)
class PlayerInventoryItemSnapshot:
    slot: int
    item: ItemNbt
    revision: int = 0

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlayerInventoryItemSnapshot":
        return cls(
            slot=int(value["slot"]),
            item=deepcopy(dict(value["item"])),
            revision=int(value.get("revision", 0)),
        )


@dataclass(slots=True)
class PlayerInventorySnapshot:
    player_name: str
    xuid: str
    selected_hotbar_slot: int
    main_size: int
    armor_size: int = 4
    offhand_size: int = 1
    ender_chest_size: int = 0
    main: list[PlayerInventoryItemSnapshot] = field(default_factory=list)
    armor: list[PlayerInventoryItemSnapshot] = field(default_factory=list)
    offhand: list[PlayerInventoryItemSnapshot] = field(default_factory=list)
    ender_chest: list[PlayerInventoryItemSnapshot] = field(default_factory=list)
    revision: int = 0

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlayerInventorySnapshot":
        def read_items(name: str) -> list[PlayerInventoryItemSnapshot]:
            raw = value.get(name, [])
            if not isinstance(raw, Iterable) or isinstance(raw, (str, bytes, Mapping)):
                raise TypeError(f"{name} must be a list of inventory item snapshots")
            return [PlayerInventoryItemSnapshot.from_mapping(entry) for entry in raw]

        return cls(
            player_name=str(value["player_name"]),
            xuid=str(value.get("xuid", "")),
            selected_hotbar_slot=int(value.get("selected_hotbar_slot", 0)),
            main_size=int(value.get("main_size", 0)),
            armor_size=int(value.get("armor_size", 4)),
            offhand_size=int(value.get("offhand_size", 1)),
            ender_chest_size=int(value.get("ender_chest_size", 0)),
            main=read_items("main"),
            armor=read_items("armor"),
            offhand=read_items("offhand"),
            ender_chest=read_items("ender_chest"),
            revision=int(value.get("revision", 0)),
        )


@dataclass(slots=True)
class PlayerInventoryPatch:
    expected_revision: int | None = None
    main_updates: dict[int, ItemNbt] = field(default_factory=dict)
    main_removals: set[int] = field(default_factory=set)
    armor_updates: dict[int, ItemNbt] = field(default_factory=dict)
    armor_removals: set[int] = field(default_factory=set)
    offhand_updates: dict[int, ItemNbt] = field(default_factory=dict)
    offhand_removals: set[int] = field(default_factory=set)
    ender_chest_updates: dict[int, ItemNbt] = field(default_factory=dict)
    ender_chest_removals: set[int] = field(default_factory=set)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "expected_revision": self.expected_revision,
            "main_updates": deepcopy(self.main_updates),
            "main_removals": sorted(self.main_removals),
            "armor_updates": deepcopy(self.armor_updates),
            "armor_removals": sorted(self.armor_removals),
            "offhand_updates": deepcopy(self.offhand_updates),
            "offhand_removals": sorted(self.offhand_removals),
            "ender_chest_updates": deepcopy(self.ender_chest_updates),
            "ender_chest_removals": sorted(self.ender_chest_removals),
        }


@dataclass(frozen=True, slots=True)
class PlayerStorageItemReference:
    section: PlayerInventorySection
    slot: int
    item: ItemNbt
    revision: int = 0


class PlayerInventoryView:
    """Detached view used to inspect or prepare optimistic player inventory writes."""

    def __init__(self, snapshot: PlayerInventorySnapshot) -> None:
        self.snapshot = deepcopy(snapshot)

    def capacity(self, section: PlayerInventorySection | str) -> int:
        section = PlayerInventorySection(section)
        return {
            PlayerInventorySection.MAIN: self.snapshot.main_size,
            PlayerInventorySection.ARMOR: self.snapshot.armor_size,
            PlayerInventorySection.OFFHAND: self.snapshot.offhand_size,
            PlayerInventorySection.ENDER_CHEST: self.snapshot.ender_chest_size,
        }[section]

    def items(self, section: PlayerInventorySection | str) -> list[PlayerInventoryItemSnapshot]:
        section = PlayerInventorySection(section)
        values = {
            PlayerInventorySection.MAIN: self.snapshot.main,
            PlayerInventorySection.ARMOR: self.snapshot.armor,
            PlayerInventorySection.OFFHAND: self.snapshot.offhand,
            PlayerInventorySection.ENDER_CHEST: self.snapshot.ender_chest,
        }[section]
        return deepcopy(values)

    def get_item(self, section: PlayerInventorySection | str, slot: int) -> ItemNbt | None:
        section = PlayerInventorySection(section)
        self._check_slot(section, slot)
        for entry in self.items(section):
            if entry.slot == slot:
                return deepcopy(entry.item)
        return None

    def patch_item(
        self,
        section: PlayerInventorySection | str,
        slot: int,
        item: ItemNbt,
    ) -> PlayerInventoryPatch:
        section = PlayerInventorySection(section)
        self._check_slot(section, slot)
        if not isinstance(item, dict):
            raise TypeError("player inventory item must be an NBT mapping")
        patch = PlayerInventoryPatch(expected_revision=self.snapshot.revision)
        self._updates(patch, section)[slot] = deepcopy(item)
        return patch

    def clear_item(
        self,
        section: PlayerInventorySection | str,
        slot: int,
    ) -> PlayerInventoryPatch:
        section = PlayerInventorySection(section)
        self._check_slot(section, slot)
        patch = PlayerInventoryPatch(expected_revision=self.snapshot.revision)
        self._removals(patch, section).add(slot)
        return patch

    def storage_item(
        self,
        section: PlayerInventorySection | str,
        slot: int,
        rules: StorageItemRules = StorageItemRules(),
    ) -> StorageItemView:
        item = self.get_item(section, slot)
        if item is None:
            raise ValueError("the selected player inventory slot is empty")
        return StorageItemView(item, rules)

    def patch_storage_item(
        self,
        section: PlayerInventorySection | str,
        slot: int,
        storage_item: StorageItemView,
    ) -> PlayerInventoryPatch:
        return self.patch_item(section, slot, storage_item.item)

    def find_storage_items(self) -> list[PlayerStorageItemReference]:
        found: list[PlayerStorageItemReference] = []
        for section in PlayerInventorySection:
            for entry in self.items(section):
                if is_storage_item_nbt(entry.item):
                    found.append(
                        PlayerStorageItemReference(
                            section=section,
                            slot=entry.slot,
                            item=deepcopy(entry.item),
                            revision=entry.revision,
                        )
                    )
        return found

    def _check_slot(self, section: PlayerInventorySection, slot: int) -> None:
        if isinstance(slot, bool) or not isinstance(slot, int):
            raise TypeError("player inventory slot must be an integer")
        if not 0 <= slot < self.capacity(section):
            raise IndexError("player inventory slot is outside the section capacity")

    @staticmethod
    def _updates(patch: PlayerInventoryPatch, section: PlayerInventorySection) -> dict[int, ItemNbt]:
        return {
            PlayerInventorySection.MAIN: patch.main_updates,
            PlayerInventorySection.ARMOR: patch.armor_updates,
            PlayerInventorySection.OFFHAND: patch.offhand_updates,
            PlayerInventorySection.ENDER_CHEST: patch.ender_chest_updates,
        }[section]

    @staticmethod
    def _removals(patch: PlayerInventoryPatch, section: PlayerInventorySection) -> set[int]:
        return {
            PlayerInventorySection.MAIN: patch.main_removals,
            PlayerInventorySection.ARMOR: patch.armor_removals,
            PlayerInventorySection.OFFHAND: patch.offhand_removals,
            PlayerInventorySection.ENDER_CHEST: patch.ender_chest_removals,
        }[section]


def _load_live_bridge() -> Any:
    errors: list[str] = []
    for module_name in (
        "endstone_blockdata._endstone_blockdata_live",
        "endstone_blockdata_inspector._endstone_blockdata_live",
        "_endstone_blockdata_live",
    ):
        try:
            return import_module(module_name)
        except ImportError as exc:
            errors.append(f"{module_name}: {exc}")
    raise RuntimeError(
        "the native BlockData live bridge is not installed; tried " + "; ".join(errors)
    )


class LivePlayerInventoryAdapter:
    """Python wrapper around the exact native ``endstone:player_inventory:v1`` service."""

    def __init__(self, server: Any, bridge: Any | None = None) -> None:
        self.server = server
        self.bridge = bridge or _load_live_bridge()

    @property
    def available(self) -> bool:
        return bool(self.bridge.player_inventory_available(self.server))

    def capabilities(self) -> dict[str, Any]:
        return dict(self.bridge.player_inventory_capabilities(self.server))

    def capture(self, player: Any) -> PlayerInventorySnapshot | None:
        raw = self.bridge.capture_player_inventory(self.server, player)
        if raw is None:
            return None
        return PlayerInventorySnapshot.from_mapping(raw)

    def apply(
        self,
        player: Any,
        patch: PlayerInventoryPatch,
        conflict_policy: str = "fail_if_changed",
    ) -> dict[str, Any]:
        return dict(
            self.bridge.apply_player_inventory(
                self.server,
                player,
                patch.to_mapping(),
                conflict_policy,
            )
        )
