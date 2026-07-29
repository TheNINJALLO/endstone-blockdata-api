"""Helpers for reading and editing bundle and ``minecraft:storage_item`` NBT."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping

from .model import BlockPatch, BlockSnapshot

STORAGE_ITEM_CONTENTS_KEY = "storage_item_component_content"
DEFAULT_STORAGE_ITEM_SLOT_CAPACITY = 64
DEFAULT_STORAGE_ITEM_MAX_WEIGHT = 64
DEFAULT_NESTED_STORAGE_ITEM_WEIGHT = 4
MAX_STORAGE_ITEM_NESTING_DEPTH = 8

ItemNbt = dict[str, Any]
StorageItemWeightResolver = Callable[[str, ItemNbt], int | None]
MaxStackSizeSource = Mapping[str, int] | Callable[[str], int | None]


class StorageItemStatus(str, Enum):
    VALID = "valid"
    WEIGHT_UNKNOWN = "weight_unknown"
    NOT_STORAGE_ITEM = "not_storage_item"
    INVALID_ITEM = "invalid_item"
    INVALID_CONTENTS = "invalid_contents"
    DUPLICATE_SLOT = "duplicate_slot"
    SLOT_OUT_OF_RANGE = "slot_out_of_range"
    FORBIDDEN_ITEM = "forbidden_item"
    NESTED_STORAGE_DISABLED = "nested_storage_disabled"
    OVERWEIGHT = "overweight"
    NESTING_TOO_DEEP = "nesting_too_deep"
    CONTENTS_UNAVAILABLE = "contents_unavailable"


@dataclass(frozen=True, slots=True)
class StorageItemRules:
    slot_capacity: int = DEFAULT_STORAGE_ITEM_SLOT_CAPACITY
    max_weight: int = DEFAULT_STORAGE_ITEM_MAX_WEIGHT
    nested_storage_item_weight: int = DEFAULT_NESTED_STORAGE_ITEM_WEIGHT
    allow_nested_storage_items: bool = True
    reject_shulker_boxes: bool = True
    allowed_items: frozenset[str] = field(default_factory=frozenset)
    banned_items: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if (
            isinstance(self.slot_capacity, bool)
            or not isinstance(self.slot_capacity, int)
            or not 1 <= self.slot_capacity <= 64
        ):
            raise ValueError("storage item slot capacity must be between 1 and 64")
        if (
            isinstance(self.max_weight, bool)
            or not isinstance(self.max_weight, int)
            or not 1 <= self.max_weight <= 64
        ):
            raise ValueError("storage item maximum weight must be between 1 and 64")
        if (
            isinstance(self.nested_storage_item_weight, bool)
            or not isinstance(self.nested_storage_item_weight, int)
            or not 0 <= self.nested_storage_item_weight <= self.max_weight
        ):
            raise ValueError("nested storage item weight is outside the supported range")


@dataclass(frozen=True, slots=True)
class StorageItemEntry:
    slot: int
    item: ItemNbt


@dataclass(frozen=True, slots=True)
class StorageItemValidation:
    status: StorageItemStatus
    message: str
    used_weight: int = 0
    exact_weight: bool = False

    @property
    def ok(self) -> bool:
        return self.status in {StorageItemStatus.VALID, StorageItemStatus.WEIGHT_UNKNOWN}


def _identifier(item: ItemNbt) -> str | None:
    for key in ("Name", "name", "id"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _count(item: ItemNbt) -> int | None:
    value = item.get("Count", item.get("count", 1))
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 255:
        return None
    return value


def _tag(item: ItemNbt, *, create: bool = False) -> ItemNbt | None:
    value = item.get("tag", item.get("user_data"))
    if value is None and create:
        value = {}
        item["tag"] = value
    return value if isinstance(value, dict) else None


def _has_tag_field(item: ItemNbt) -> bool:
    return "tag" in item or "user_data" in item


def _contents(item: ItemNbt) -> list[ItemNbt] | None:
    tag = _tag(item)
    if tag is None:
        return None
    value = tag.get(STORAGE_ITEM_CONTENTS_KEY)
    return value if isinstance(value, list) else None


def _has_contents_field(item: ItemNbt) -> bool:
    tag = _tag(item)
    return tag is not None and STORAGE_ITEM_CONTENTS_KEY in tag


def is_vanilla_bundle_identifier(identifier: str) -> bool:
    if not identifier.startswith("minecraft:"):
        return False
    name = identifier.removeprefix("minecraft:")
    return name == "bundle" or name.endswith("_bundle")


def is_storage_item_nbt(item: ItemNbt) -> bool:
    identifier = _identifier(item)
    return bool(identifier and is_vanilla_bundle_identifier(identifier)) or _has_contents_field(item)


def _is_shulker_box(identifier: str) -> bool:
    if not identifier.startswith("minecraft:"):
        return False
    name = identifier.removeprefix("minecraft:")
    return name in {"shulker_box", "undyed_shulker_box"} or name.endswith("_shulker_box")


def storage_weight_from_max_stack_size(max_stack_size: int, max_weight: int = 64) -> int:
    if isinstance(max_stack_size, bool) or not 1 <= max_stack_size <= 255:
        raise ValueError("max stack size must be between 1 and 255")
    if isinstance(max_weight, bool) or max_weight < 1:
        raise ValueError("maximum weight must be positive")
    return (max_weight + max_stack_size - 1) // max_stack_size


def make_max_stack_size_weight_resolver(
    source: MaxStackSizeSource,
    max_weight: int = 64,
) -> StorageItemWeightResolver:
    def resolve(identifier: str, _item: ItemNbt) -> int | None:
        value = source.get(identifier) if isinstance(source, Mapping) else source(identifier)
        if value is None:
            return None
        return storage_weight_from_max_stack_size(value, max_weight)

    return resolve


def _embedded_weight(item: ItemNbt, max_weight: int) -> int | None:
    for key in ("_endstone_storage_weight", "StorageWeight", "storage_weight"):
        value = item.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    for key in ("_endstone_max_stack_size", "MaxStackSize", "max_stack_size"):
        value = item.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            try:
                return storage_weight_from_max_stack_size(value, max_weight)
            except ValueError:
                return -1
    return None


def validate_storage_item(
    item: ItemNbt,
    rules: StorageItemRules = StorageItemRules(),
    weight_resolver: StorageItemWeightResolver | None = None,
    *,
    _depth: int = 0,
) -> StorageItemValidation:
    if _depth > MAX_STORAGE_ITEM_NESTING_DEPTH:
        return StorageItemValidation(
            StorageItemStatus.NESTING_TOO_DEEP,
            "storage item nesting exceeds the supported depth",
        )
    if not isinstance(item, dict):
        return StorageItemValidation(StorageItemStatus.INVALID_ITEM, "storage item must be an item compound")

    identifier = _identifier(item)
    item_count = _count(item)
    if identifier is None or item_count is None:
        return StorageItemValidation(
            StorageItemStatus.INVALID_ITEM,
            "storage item must contain a valid item identifier and count",
        )

    contents = _contents(item)
    if contents is None:
        if _has_contents_field(item):
            return StorageItemValidation(
                StorageItemStatus.INVALID_CONTENTS,
                "storage_item_component_content must be a list",
            )
        if _has_tag_field(item) and _tag(item) is None:
            return StorageItemValidation(
                StorageItemStatus.INVALID_CONTENTS,
                "storage item tag must be an NBT compound",
            )
        if is_vanilla_bundle_identifier(identifier):
            return StorageItemValidation(
                StorageItemStatus.CONTENTS_UNAVAILABLE,
                "storage item contents are unavailable",
            )
        return StorageItemValidation(
            StorageItemStatus.NOT_STORAGE_ITEM,
            "item has no storage_item_component_content list",
        )

    if len(contents) > rules.slot_capacity:
        return StorageItemValidation(
            StorageItemStatus.INVALID_CONTENTS,
            "storage item has more entries than its slot capacity",
        )

    occupied: set[int] = set()
    used_weight = 0
    exact_weight = True

    for entry in contents:
        if not isinstance(entry, dict):
            return StorageItemValidation(
                StorageItemStatus.INVALID_CONTENTS,
                "storage item entries must be item compounds",
                used_weight,
                exact_weight,
            )

        slot = entry.get("Slot", entry.get("slot"))
        if isinstance(slot, bool) or not isinstance(slot, int):
            return StorageItemValidation(
                StorageItemStatus.INVALID_CONTENTS,
                "storage item entry is missing a valid Slot",
                used_weight,
                exact_weight,
            )
        if not 0 <= slot < rules.slot_capacity:
            return StorageItemValidation(
                StorageItemStatus.SLOT_OUT_OF_RANGE,
                "storage item slot is outside the supported range",
                used_weight,
                exact_weight,
            )
        if slot in occupied:
            return StorageItemValidation(
                StorageItemStatus.DUPLICATE_SLOT,
                "storage item contains a duplicate slot",
                used_weight,
                exact_weight,
            )
        occupied.add(slot)

        nested_identifier = _identifier(entry)
        count = _count(entry)
        if nested_identifier is None or count is None:
            return StorageItemValidation(
                StorageItemStatus.INVALID_ITEM,
                "storage item contains an invalid item entry",
                used_weight,
                exact_weight,
            )

        if rules.allowed_items and nested_identifier not in rules.allowed_items:
            return StorageItemValidation(
                StorageItemStatus.FORBIDDEN_ITEM,
                "item is not included in the storage item's allowed-items list",
                used_weight,
                exact_weight,
            )
        if nested_identifier in rules.banned_items or (
            rules.reject_shulker_boxes and _is_shulker_box(nested_identifier)
        ):
            return StorageItemValidation(
                StorageItemStatus.FORBIDDEN_ITEM,
                "item is banned from this storage item",
                used_weight,
                exact_weight,
            )

        if is_storage_item_nbt(entry):
            if not rules.allow_nested_storage_items:
                return StorageItemValidation(
                    StorageItemStatus.NESTED_STORAGE_DISABLED,
                    "nested storage items are disabled",
                    used_weight,
                    exact_weight,
                )
            if count != 1:
                return StorageItemValidation(
                    StorageItemStatus.INVALID_ITEM,
                    "nested storage items must have a count of one",
                    used_weight,
                    exact_weight,
                )
            nested = validate_storage_item(
                entry,
                rules,
                weight_resolver,
                _depth=_depth + 1,
            )
            if not nested.ok:
                return nested
            used_weight += nested.used_weight + rules.nested_storage_item_weight
            exact_weight = exact_weight and nested.exact_weight
        else:
            unit_weight = _embedded_weight(entry, rules.max_weight)
            if unit_weight is None and weight_resolver is not None:
                unit_weight = weight_resolver(nested_identifier, entry)
            if unit_weight is None:
                unit_weight = 1
                exact_weight = False
            if isinstance(unit_weight, bool) or not isinstance(unit_weight, int) or not 1 <= unit_weight <= rules.max_weight:
                return StorageItemValidation(
                    StorageItemStatus.INVALID_ITEM,
                    "item weight resolver returned an invalid value",
                    used_weight,
                    exact_weight,
                )
            used_weight += unit_weight * count

        if used_weight > rules.max_weight:
            return StorageItemValidation(
                StorageItemStatus.OVERWEIGHT,
                "storage item exceeds its weight limit",
                used_weight,
                exact_weight,
            )

    if not exact_weight:
        return StorageItemValidation(
            StorageItemStatus.WEIGHT_UNKNOWN,
            "storage layout is valid, but exact weight requires item-weight information",
            used_weight,
            False,
        )
    return StorageItemValidation(
        StorageItemStatus.VALID,
        "storage item is valid",
        used_weight,
        True,
    )


class StorageItemView:
    """A detached, editable view of one storage item with serialized contents.

    ``create_if_missing`` is reserved for intentionally authoring a new,
    known-empty serialized storage item. Captured items fail closed when their
    contents payload is unavailable.
    """

    def __init__(
        self,
        item: ItemNbt,
        rules: StorageItemRules = StorageItemRules(),
        *,
        create_if_missing: bool = False,
    ) -> None:
        if not isinstance(item, dict) or _identifier(item) is None:
            raise ValueError("storage item must be an item compound with an identifier")
        if not is_storage_item_nbt(item) and not create_if_missing:
            raise ValueError("item is not a bundle or serialized storage item")
        self._item = deepcopy(item)
        self.rules = rules
        self._mutable_contents(create_if_missing=create_if_missing)

    @property
    def item(self) -> ItemNbt:
        return deepcopy(self._item)

    @property
    def item_identifier(self) -> str:
        value = _identifier(self._item)
        if value is None:
            raise RuntimeError("storage item has no item identifier")
        return value

    @property
    def contents(self) -> list[StorageItemEntry]:
        contents = _contents(self._item)
        if contents is None:
            raise RuntimeError("storage item contents are unavailable")
        result: list[StorageItemEntry] = []
        for entry in contents:
            if not isinstance(entry, dict):
                raise ValueError("storage item entry must be an item compound")
            slot = entry.get("Slot", entry.get("slot"))
            if isinstance(slot, bool) or not isinstance(slot, int):
                raise ValueError("storage item entry is missing a valid Slot")
            result.append(StorageItemEntry(slot, deepcopy(entry)))
        return sorted(result, key=lambda value: value.slot)

    def get_item(self, slot: int) -> ItemNbt | None:
        self._check_slot(slot)
        for entry in self.contents:
            if entry.slot == slot:
                return deepcopy(entry.item)
        return None

    def set_item(self, slot: int, item: ItemNbt) -> StorageItemView:
        self._check_slot(slot)
        if not isinstance(item, dict) or _identifier(item) is None or _count(item) is None:
            raise ValueError("storage item entry must be a valid item compound")
        replacement = deepcopy(item)
        replacement["Slot"] = slot
        contents = self._mutable_contents()
        contents[:] = [
            entry
            for entry in contents
            if not isinstance(entry, dict) or entry.get("Slot", entry.get("slot")) != slot
        ]
        contents.append(replacement)

        def slot_key(entry: object) -> int:
            if not isinstance(entry, dict):
                return self.rules.slot_capacity
            value = entry.get("Slot", entry.get("slot"))
            return value if isinstance(value, int) and not isinstance(value, bool) else self.rules.slot_capacity

        contents.sort(key=slot_key)
        return self

    def clear_item(self, slot: int) -> StorageItemView:
        self._check_slot(slot)
        contents = self._mutable_contents()
        contents[:] = [
            entry
            for entry in contents
            if not isinstance(entry, dict) or entry.get("Slot", entry.get("slot")) != slot
        ]
        return self

    def replace_contents(self, entries: list[StorageItemEntry]) -> StorageItemView:
        candidate = StorageItemView(self._item, self.rules)
        candidate._mutable_contents().clear()
        occupied: set[int] = set()
        for entry in entries:
            if entry.slot in occupied:
                raise ValueError("replacement contents contain a duplicate slot")
            occupied.add(entry.slot)
            candidate.set_item(entry.slot, entry.item)
        self._item = candidate._item
        return self

    def validate(
        self,
        weight_resolver: StorageItemWeightResolver | None = None,
    ) -> StorageItemValidation:
        return validate_storage_item(self._item, self.rules, weight_resolver)

    def patch_parent(self, snapshot: BlockSnapshot, parent_slot: int) -> BlockPatch:
        """Create a normal BlockData inventory patch for the bundle's parent slot."""
        if parent_slot < 0:
            raise ValueError("parent slot must be non-negative")
        return BlockPatch(
            snapshot.location,
            snapshot.revision,
            inventory_updates={parent_slot: self.item},
        )

    def _mutable_contents(self, *, create_if_missing: bool = False) -> list[ItemNbt]:
        tag = _tag(self._item, create=create_if_missing)
        if tag is None:
            if _has_tag_field(self._item):
                raise ValueError("storage item tag must be an NBT compound")
            if not create_if_missing:
                raise ValueError("storage item contents are unavailable")
            raise RuntimeError("failed to initialize storage item tag")
        if STORAGE_ITEM_CONTENTS_KEY not in tag:
            if not create_if_missing:
                raise ValueError("storage item contents are unavailable")
            tag[STORAGE_ITEM_CONTENTS_KEY] = []
        value = tag[STORAGE_ITEM_CONTENTS_KEY]
        if not isinstance(value, list):
            raise ValueError("storage_item_component_content must be a list")
        return value

    def _check_slot(self, slot: int) -> None:
        if isinstance(slot, bool) or not isinstance(slot, int) or not 0 <= slot < self.rules.slot_capacity:
            raise IndexError("storage item slot is outside the supported range")
