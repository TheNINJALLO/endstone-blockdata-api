# Live Shelf API

BlockData exposes vanilla shelves and chiseled bookshelves through `ShelfView`.
The view refuses partial captures, the wrong actor type, capacity mismatches,
duplicate slots, and out-of-range entries instead of treating them as empty.

| Actor | Capacity | Slot rule |
|---|---:|---|
| `minecraft:shelf` | 3 | Any item accepted by the live container |
| `minecraft:chiseled_bookshelf` | 6 | One book, writable book, written book, or enchanted book per slot |

Only occupied slots appear in a native snapshot. `ShelfView.slots` expands that
sparse list to the actor's exact capacity so an empty slot is unambiguous.

## Live Python usage

```python
from endstone_blockdata import (
    BlockDataService,
    BlockLocation,
    ConflictPolicy,
    LiveBlockDataAdapter,
    ShelfView,
)

service = BlockDataService(LiveBlockDataAdapter(self.server))
location = BlockLocation("overworld", 100, 64, 200)
snapshot = service.capture(location.dimension, (location.x, location.y, location.z))
if snapshot is None:
    raise RuntimeError("shelf chunk is unavailable")

shelf = ShelfView(snapshot)
print(shelf.kind, shelf.capacity, shelf.slots)

# One slot. The snapshot revision makes this a compare-and-swap write.
result = service.apply(
    shelf.patch_item(0, {"Name": "minecraft:diamond", "Count": 8}),
    ConflictPolicy.FAIL_IF_CHANGED,
)

# Multiple slots are still one actor-level write and one revision check.
batch = shelf.patch_items(
    updates={1: {"Name": "minecraft:emerald", "Count": 4}},
    removals={2},
)
result = service.apply(batch, ConflictPolicy.FAIL_IF_CHANGED)
```

`replace_items()` requires exactly 3 or 6 entries and changes the whole shelf
in one call. A `None` entry clears that slot.

## Shelf shop example

[`examples/python/shelf_shop.py`](../examples/python/shelf_shop.py) implements a
three-product visual shop stock manager. It keeps price/catalog data outside
block-actor NBT, validates that a listed slot still contains the configured
product, reserves stock with the shelf revision, and offers a compensating
restore operation when a later payment or player-item grant fails.

Each reservation carries a unique ID, a detached item payload, and its
post-reservation shelf revision. `ShelfShop` keeps an independent active record
for every ID. Restore rejects unknown IDs, altered or forged tokens, replay, and
any shelf revision change before it writes stock back. Persist the complete
active record in a production purchase journal; the example's authenticated
in-memory registry does not survive a process restart.

A BlockData shelf write and a player-inventory or economy write are separate
transactions. For a production shop, persist a purchase ID and state before
the first mutation, then record `stock_reserved`, `payment_debited`, and
`item_granted` transitions. On restart, retry the missing step or call
`ShelfShop.restore()`; do not claim cross-service atomicity.

## Native behavior and safety

The exact adapter uses the live actor's `Container` interface, validates the
runtime capacity, sends slot/container/block-entity change notifications, and
reads the complete container back after a write. A rejected or canonicalized
write is rolled back and reported as an adapter error. Arbitrary shelf actor
NBT remains read-only until the exact display/powered-state load ABI is proven;
inventory editing is the supported production surface.
