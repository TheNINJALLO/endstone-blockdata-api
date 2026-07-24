# Canonical NBT & Container Item System

The **Endstone BlockData API** provides direct access to canonical Minecraft Bedrock block entity NBT tags and container inventories.

---

## 📦 `ContainerView`

`ContainerView` is a lightweight helper wrapper around a `BlockSnapshot` that contains a block entity.

### Constructor
```python
from endstone_blockdata import ContainerView

view = ContainerView(snapshot)
```

### Properties
- `view.nbt`: Returns a deep copy of the raw canonical NBT dictionary (e.g. `CustomName`, `Lock`, `Items`).
- `view.raw_snbt`: Returns the Stringified NBT (SNBT) text representation.

---

## 🔨 Container Slot Item Manipulation

### 1. Reading an Item Slot
```python
item = view.get_item(slot=0)
# Returns: {"id": "minecraft:diamond", "count": 64, "tag": {...}} or None if empty
```

### 2. Patching an Item Slot
To add or update an item in a specific container slot, generate a `BlockPatch` using `view.patch_item(slot, item_dict)`:

```python
item_payload = {
    "id": "minecraft:netherite_sword",
    "count": 1,
    "tag": {
        "display": {
            "Name": "§cBlade of Ruin",
            "Lore": ["§7Forged in ancient flames"]
        },
        "ench": [
            {"id": 9, "lvl": 5}  # Sharpness V
        ]
    }
}

patch = view.patch_item(0, item_payload)
result = service.apply(patch, ConflictPolicy.FORCE)
```

### 3. Clearing an Item Slot
```python
patch = view.clear_item(slot=0)
result = service.apply(patch, ConflictPolicy.FORCE)
```
