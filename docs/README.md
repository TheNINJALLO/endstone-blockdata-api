# Endstone BlockData API Wiki & Technical Manual

Welcome to the official documentation and technical wiki for **Endstone BlockData API**.

This library provides high-performance, native Bedrock block state mutation, canonical container NBT inspection, and transaction audit recording for **Endstone Minecraft Bedrock Edition** servers.

---

## 🎯 Quick Navigation

- [🏗️ Architecture & Core Concepts](ARCHITECTURE.md) — Learn about memory snapshots, optimistic revision checks, and collision handling policies.
- [📦 Container NBT & Item Manipulation](nbt_and_containers.md) — Inspect container slots, read/write canonical NBT, and modify item tags in real-time.
- [🛡️ Anti-Grief Transaction Audit Recorder](audit_system.md) — Record baseline container snapshots and calculate delta inventory changes.
- [🎮 In-Game Command Suite Guide](in_game_testing.md) — Full reference for the `/bd` command suite and packaged test plugin wheel.
- [📘 Complete API Reference](api_reference.md) — Comprehensive class, interface, and method reference for C++ and Python.

---

## ⚡ Basic Example

```python
from endstone_blockdata import BlockDataService, ContainerView, ConflictPolicy

service = BlockDataService()
snapshot = service.capture("overworld", (100, 64, 200))

if snapshot.block_entity:
    view = ContainerView(snapshot)
    patch = view.patch_item(0, {
        "id": "minecraft:diamond",
        "count": 64,
        "tag": {"display": {"Name": "§6Super Diamond"}}
    })
    result = service.apply(patch, ConflictPolicy.FORCE)
    print("Item Patched:", result.success)
```
