# Complete API Reference

Complete class, function, and parameter specification for `endstone_blockdata`.

---

## 1. `BlockDataService`

### `capture(dimension: str, position: tuple[int, int, int]) -> BlockSnapshot`
Captures block state traits and canonical NBT snapshot at target coordinates.

### `apply(patch: BlockPatch, policy: ConflictPolicy) -> ApplyResult`
Applies state and NBT mutations atomically with optimism collision policy.

### `capture_region(dimension: str, minimum: tuple[int,int,int], maximum: tuple[int,int,int]) -> list[BlockSnapshot]`
Captures all block snapshots within a 3D bounding box.

### `diff(before: BlockSnapshot, after: BlockSnapshot) -> BlockEntityAuditDelta`
Calculates inventory item and block state deltas between two snapshots.

---

## 2. Data Models

### `BlockSnapshot`
- `location: BlockLocation`
- `type: str`
- `runtime_id: int`
- `states: dict[str, str]`
- `revision: int`
- `block_entity: BlockEntitySnapshot | None`

### `BlockPatch`
- `location: BlockLocation`
- `expected_revision: int | None`
- `replacement_type: str | None`
- `state_updates: dict[str, str]`
- `inventory_updates: dict[int, dict]`
- `inventory_removals: set[int]`

### `ConflictPolicy`
- `ConflictPolicy.FAIL_IF_CHANGED`: Rejects patch if revision does not match expected revision.
- `ConflictPolicy.FORCE`: Forces patch application regardless of revision.
