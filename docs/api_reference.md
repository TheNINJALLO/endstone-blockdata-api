# Python API Reference

The release command wheel vendors the `endstone_blockdata` package and its
matching native bridge. These are the main public Python surfaces.

## Live service

### `LiveBlockDataAdapter(server, bridge=None)`

Connects `BlockDataService` to the native `endstone:blockdata:v2` service. The
optional bridge argument exists for testing and custom embedding; passing an
explicit object never falls back merely because that object is falsey.

### `BlockDataService(adapter=None)`

With no adapter, the service uses `InMemoryAdapter` for detached tests. Use
`BlockDataService(LiveBlockDataAdapter(plugin.server))` for a live server.

- `capture(dimension, position) -> BlockSnapshot | None` captures one block.
- `capture_region(dimension, minimum, maximum) -> list[BlockSnapshot]` captures
  at most 32,768 blocks. A live adapter delegates this as one native region
  request; other adapters use bounded per-block capture.
- `apply(patch, policy=ConflictPolicy.FAIL_IF_CHANGED) -> ApplyResult` forwards
  an optimistic patch to the adapter.
- `diff(before, after) -> BlockEntityAuditDelta` compares block, actor NBT, and
  occupied inventory.

Patch support and atomicity are adapter-specific. The exact live adapter
rejects unsupported policies and mixed mutation surfaces instead of promising
cross-surface atomicity. Prefer `FAIL_IF_CHANGED`; `FORCE` deliberately ignores
the expected revision.

## Container and shelf views

### `ContainerView(snapshot)`

Creates a detached view of a captured block entity.

- `capacity` reports the live container size.
- `occupied_slots` reports the sparse occupied count.
- `get_item(slot)` returns a detached item mapping or `None`.
- `patch_item(slot, item)` and `clear_item(slot)` create revision-bound patches.

### `ShelfView(snapshot)`

Accepts only a complete three-slot `minecraft:shelf` or six-slot
`minecraft:chiseled_bookshelf` capture. It rejects actor/capacity mismatches,
duplicate slots, invalid slot numbers, and invalid chiseled-book writes.

- `kind`, `capacity`, and `slots` expose the typed shelf layout.
- `get_item(slot)` reads one detached slot.
- `patch_item`, `clear_item`, and `patch_items` build optimistic slot patches.
- `replace_items(items)` requires exactly the actor's full capacity.

See [Live Shelf API](shelves.md) for the revision-safe shop example.

## Storage items and player inventory

`StorageItemView`, `StorageItemRules`, and `validate_storage_item` read and edit
serialized bundle or custom storage-item contents. Missing serialized contents
return `StorageItemStatus.CONTENTS_UNAVAILABLE`; they are never treated as an
empty bundle. See [Bundle and Storage Item Module](storage_items.md).

`LivePlayerInventoryAdapter`, `PlayerInventoryView`,
`PlayerInventorySection`, and `PlayerInventoryPatch` expose live main, armor,
offhand, and Ender Chest snapshots. See [Player Inventory Adapter](player_inventory.md).

## Core data models

### `BlockSnapshot`

- `location: BlockLocation`
- `type: str`
- `runtime_id: int`
- `states: dict[str, bool | int | str]`
- `revision: int`
- `block_entity: BlockEntitySnapshot | None`
- `block_entity_status: str`

The revision fingerprints block/state data, actor NBT, occupied inventory,
capture completeness, and container flag/capacity. Inventory storage order does
not affect it.

### `BlockEntitySnapshot`

- `type: str`
- `nbt: dict`
- `raw_snbt: str`
- `canonical_nbt: bool`
- `is_container: bool`
- `container_size: int`
- `inventory: list[InventorySlotSnapshot]` (occupied slots only)

### `BlockPatch`

- `location: BlockLocation`
- `expected_revision: int | None`
- `replacement_type: str | None`
- `state_updates: dict[str, bool | int | str]`
- `state_removals: set[str]`
- `nbt_updates: dict[str, object]`
- `nbt_removals: set[str]`
- `inventory_updates: dict[int, dict]`
- `inventory_removals: set[int]`

### `ApplyResult`

- `ok: bool`
- `status: str`
- `message: str`
- `resulting_revision: int`
