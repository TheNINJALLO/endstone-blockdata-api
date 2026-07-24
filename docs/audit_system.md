# Container Transaction Audit & Anti-Grief Recorder

The audit system allows server admins and plugins to track item transactions, container thefts, and block state modifications by comparing snapshots.

---

## 🔍 How Snapshot Diffing Works

`BlockDataService.diff(before, after)` compares two `BlockSnapshot` instances taken at different times at the exact same location.

```python
from endstone_blockdata import BlockDataService

service = BlockDataService()

# 1. Capture baseline snapshot when player opens container
before = service.capture("overworld", (100, 64, 200))

# ... Container interaction occurs ...

# 2. Capture snapshot after interaction finishes
after = service.capture("overworld", (100, 64, 200))

# 3. Compute audit delta
delta = service.diff(before, after)

print("Block Type Changed:", delta.block_changed)
print("Actor NBT Changed:", delta.actor_nbt_changed)
print("Total Item Changes:", len(delta.inventory_changes))

for change in delta.inventory_changes:
    print(f"Slot {change.slot}: Kind={change.kind.name}, Before={change.before}, After={change.after}")
```

---

## 🛡️ Inventory Change Kinds

The `change.kind` enum indicates the exact nature of the change:
- `InventoryChangeKind.ADDED`: Item inserted into previously empty slot.
- `InventoryChangeKind.REMOVED`: Item taken out of slot.
- `InventoryChangeKind.CHANGED`: Item quantity, damage, or NBT modified.
