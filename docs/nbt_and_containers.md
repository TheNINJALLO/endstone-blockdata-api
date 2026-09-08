# Canonical NBT & Container Item System

The **Endstone BlockData API** provides direct access to canonical Minecraft Bedrock block entity NBT tags and container inventories.

## Native strings in Python snapshots

The live bridge exposes NBT String values and compound keys as Python `str`.
Valid UTF-8 text is unchanged. Bytes that are not valid UTF-8 are preserved using
[Python's `surrogateescape` codec handler](https://docs.python.org/3/library/codecs.html#error-handlers)
as `U+DC80`–`U+DCFF` escapes. The bridge converts them back to the original bytes
when applying block or player-inventory patches. SNBT output uses the same
decoding, so one non-UTF-8 value does not abort the entire capture.

Use `json.dumps(snapshot, ensure_ascii=True)` when storing a snapshot mapping
as JSON; `json.loads` preserves these escapes for later restore. For display,
use JSON escaping or `repr(value)` instead of sending escaped strings directly
to APIs that require strict UTF-8. To retrieve a native String tag's original
bytes, use `value.encode("utf-8", "surrogateescape")`.
Passing Python `bytes` or `bytearray` into an NBT patch still creates a ByteArray
tag, so retain captured strings as `str` to preserve their NBT type.

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
