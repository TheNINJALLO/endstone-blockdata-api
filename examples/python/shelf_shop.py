"""Shelf-backed shop stock example for the live BlockData API.

This module owns shelf stock only. A real economy plugin should persist a
purchase journal before changing currency or player inventory because those
services cannot be committed atomically with a block-container write.

Call ``reserve()`` before charging/granting. Call ``complete()`` after both
external steps succeed, or ``restore()`` after either step fails. Both terminal
operations consume the signed-in-memory reservation token and reject replays.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Mapping
from uuid import uuid4

from endstone_blockdata import (
    ApplyResult,
    BlockDataService,
    BlockLocation,
    ConflictPolicy,
    LiveBlockDataAdapter,
    ShelfKind,
    ShelfView,
)

ItemNbt = dict[str, Any]


def _item_identifier(item: ItemNbt) -> str:
    for key in ("Name", "name", "id"):
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    raise ValueError("shop stock item has no identifier")


def _item_count(item: ItemNbt) -> int:
    value = item.get("Count", item.get("count", 1))
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 255:
        raise ValueError("shop stock item has an invalid count")
    return value


def _with_count(item: ItemNbt, count: int) -> ItemNbt:
    output = deepcopy(item)
    output.pop("count", None)
    output["Count"] = count
    return output


@dataclass(frozen=True, slots=True)
class ShelfListing:
    slot: int
    product_id: str
    price_item_id: str
    price_count: int

    def __post_init__(self) -> None:
        if isinstance(self.slot, bool) or not isinstance(self.slot, int) or self.slot < 0:
            raise ValueError("listing slot must be a non-negative integer")
        if (
            not isinstance(self.product_id, str)
            or not self.product_id
            or not isinstance(self.price_item_id, str)
            or not self.price_item_id
        ):
            raise ValueError("listing item identifiers must not be empty")
        if (
            isinstance(self.price_count, bool)
            or not isinstance(self.price_count, int)
            or self.price_count < 1
        ):
            raise ValueError("listing price count must be positive")


@dataclass(frozen=True, slots=True)
class ShelfQuote:
    listing: ShelfListing
    stock_count: int
    item: ItemNbt | None
    shelf_revision: int


@dataclass(frozen=True, slots=True, init=False)
class StockReservation:
    reservation_id: str
    location: BlockLocation
    slot: int
    quantity: int
    shelf_revision: int
    _item: ItemNbt = field(repr=False)

    def __init__(
        self,
        reservation_id: str,
        location: BlockLocation,
        slot: int,
        item: ItemNbt,
        quantity: int,
        shelf_revision: int,
    ) -> None:
        if not isinstance(reservation_id, str) or not reservation_id:
            raise ValueError("reservation ID must not be empty")
        if not isinstance(location, BlockLocation):
            raise TypeError("reservation location must be a BlockLocation")
        if isinstance(slot, bool) or not isinstance(slot, int) or slot < 0:
            raise ValueError("reservation slot must be a non-negative integer")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("reservation quantity must be positive")
        if (
            isinstance(shelf_revision, bool)
            or not isinstance(shelf_revision, int)
            or shelf_revision < 0
        ):
            raise ValueError("reservation shelf revision must be non-negative")
        if not isinstance(item, dict):
            raise TypeError("reservation item must be an NBT mapping")
        _item_identifier(item)
        if _item_count(item) != quantity:
            raise ValueError("reservation item count must match its quantity")

        object.__setattr__(self, "reservation_id", reservation_id)
        object.__setattr__(self, "location", location)
        object.__setattr__(self, "slot", slot)
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "shelf_revision", shelf_revision)
        object.__setattr__(self, "_item", deepcopy(item))

    @property
    def item(self) -> ItemNbt:
        """Return a detached copy so callers cannot mutate the token payload."""
        return deepcopy(self._item)

    def _matches(self, other: StockReservation) -> bool:
        return (
            isinstance(other, StockReservation)
            and self.reservation_id == other.reservation_id
            and self.location == other.location
            and self.slot == other.slot
            and self.quantity == other.quantity
            and self.shelf_revision == other.shelf_revision
            and self._item == other._item
        )


class ShelfShop:
    """Revision-safe stock manager for one shelf block."""

    def __init__(
        self,
        service: BlockDataService,
        location: BlockLocation,
        listings: Mapping[int, ShelfListing],
    ) -> None:
        self.service = service
        self.location = location
        self.listings = dict(listings)
        self._reservation_lock = RLock()
        self._active_reservations: dict[str, StockReservation] = {}
        self._restored_reservations: set[str] = set()
        self._completed_reservations: set[str] = set()
        for slot, listing in self.listings.items():
            if slot != listing.slot:
                raise ValueError("listing map keys must match listing.slot")

    def _capture(self) -> ShelfView:
        snapshot = self.service.capture(
            self.location.dimension,
            (self.location.x, self.location.y, self.location.z),
        )
        if snapshot is None:
            raise RuntimeError("shop shelf or chunk is unavailable")
        shelf = ShelfView(snapshot)
        for slot in self.listings:
            if slot >= shelf.capacity:
                raise ValueError("listing slot is outside this shelf's capacity")
        return shelf

    def quotes(self) -> list[ShelfQuote]:
        shelf = self._capture()
        output: list[ShelfQuote] = []
        for slot, listing in sorted(self.listings.items()):
            item = shelf.get_item(slot)
            count = 0
            if item is not None and _item_identifier(item) == listing.product_id:
                count = _item_count(item)
            output.append(
                ShelfQuote(
                    listing,
                    count,
                    deepcopy(item),
                    shelf.snapshot.revision,
                )
            )
        return output

    def reserve(self, slot: int, quantity: int = 1) -> StockReservation:
        """Remove stock with compare-and-swap before a payment/grant step."""
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            raise ValueError("reservation quantity must be positive")
        listing = self.listings.get(slot)
        if listing is None:
            raise KeyError(f"shelf slot {slot} has no shop listing")

        shelf = self._capture()
        item = shelf.get_item(slot)
        if item is None or _item_identifier(item) != listing.product_id:
            raise RuntimeError("listed shelf slot does not contain its configured product")
        available = _item_count(item)
        if available < quantity:
            raise RuntimeError("shop shelf does not have enough stock")

        remaining = available - quantity
        patch = (
            shelf.clear_item(slot)
            if remaining == 0
            else shelf.patch_item(slot, _with_count(item, remaining))
        )
        result = self.service.apply(patch, ConflictPolicy.FAIL_IF_CHANGED)
        if not result.ok:
            raise RuntimeError(
                f"shop stock changed before reservation: {result.status}: {result.message}"
            )
        with self._reservation_lock:
            reservation_id = uuid4().hex
            while (
                reservation_id in self._active_reservations
                or reservation_id in self._restored_reservations
                or reservation_id in self._completed_reservations
            ):
                reservation_id = uuid4().hex
            reservation = StockReservation(
                reservation_id,
                self.location,
                slot,
                _with_count(item, quantity),
                quantity,
                result.resulting_revision,
            )
            # Keep an independent authoritative copy. A restore must present a
            # token that exactly matches this active record.
            self._active_reservations[reservation_id] = StockReservation(
                reservation.reservation_id,
                reservation.location,
                reservation.slot,
                reservation.item,
                reservation.quantity,
                reservation.shelf_revision,
            )
        return reservation

    def complete(self, reservation: StockReservation) -> None:
        """Finalize a successful payment/grant and consume its restore token."""
        if not isinstance(reservation, StockReservation):
            raise TypeError("complete requires a StockReservation token")
        with self._reservation_lock:
            if reservation.reservation_id in self._completed_reservations:
                raise RuntimeError("reservation has already been completed")
            if reservation.reservation_id in self._restored_reservations:
                raise RuntimeError("reservation has already been restored")
            active = self._active_reservations.get(reservation.reservation_id)
            if active is None:
                raise RuntimeError("reservation is not active for this shop")
            if not active._matches(reservation):
                raise RuntimeError("reservation token does not match the active record")
            if active.location != self.location:
                raise ValueError("reservation belongs to a different shelf")
            self._active_reservations.pop(active.reservation_id, None)
            self._completed_reservations.add(active.reservation_id)

    def restore(self, reservation: StockReservation) -> ApplyResult:
        """Compensate a failed payment/grant using another revision-safe write."""
        if not isinstance(reservation, StockReservation):
            raise TypeError("restore requires a StockReservation token")
        with self._reservation_lock:
            if reservation.reservation_id in self._completed_reservations:
                raise RuntimeError("reservation has already been completed")
            if reservation.reservation_id in self._restored_reservations:
                raise RuntimeError("reservation has already been restored")
            active = self._active_reservations.get(reservation.reservation_id)
            if active is None:
                raise RuntimeError("reservation is not active for this shop")
            if not active._matches(reservation):
                raise RuntimeError("reservation token does not match the active record")
            if active.location != self.location:
                raise ValueError("reservation belongs to a different shelf")
            shelf = self._capture()
            if shelf.snapshot.revision != active.shelf_revision:
                raise RuntimeError(
                    "reservation is stale because the shelf changed after stock was reserved"
                )
            reserved_item = active.item
            current = shelf.get_item(active.slot)
            if current is None:
                restored = reserved_item
            else:
                if _item_identifier(current) != _item_identifier(reserved_item):
                    raise RuntimeError("cannot restore stock over a different shelf item")
                restored_count = _item_count(current) + active.quantity
                if restored_count > 255:
                    raise RuntimeError("restored stock would exceed the item count limit")
                restored = _with_count(current, restored_count)
            result = self.service.apply(
                shelf.patch_item(active.slot, restored),
                ConflictPolicy.FAIL_IF_CHANGED,
            )
            if result.ok:
                self._active_reservations.pop(active.reservation_id, None)
                self._restored_reservations.add(reservation.reservation_id)
            return result

    def replace_stock(self, items: list[ItemNbt | None]) -> ApplyResult:
        """Restock every slot in one shelf-level compare-and-swap write."""
        shelf = self._capture()
        return self.service.apply(
            shelf.replace_items(items),
            ConflictPolicy.FAIL_IF_CHANGED,
        )


def create_live_shop(plugin: Any) -> ShelfShop:
    """Small Endstone plugin setup example for a three-slot vanilla shelf."""
    service = BlockDataService(LiveBlockDataAdapter(plugin.server))
    location = BlockLocation("overworld", 100, 64, 200)
    return ShelfShop(
        service,
        location,
        {
            0: ShelfListing(0, "minecraft:diamond", "minecraft:emerald", 8),
            1: ShelfListing(1, "minecraft:gold_ingot", "minecraft:emerald", 2),
            2: ShelfListing(2, "minecraft:bread", "minecraft:emerald", 1),
        },
    )


def require_normal_shelf(shop: ShelfShop) -> None:
    """Optional startup validation for the visual three-product shop layout."""
    if shop._capture().kind is not ShelfKind.SHELF:
        raise RuntimeError("this shop example requires a normal three-slot shelf")
