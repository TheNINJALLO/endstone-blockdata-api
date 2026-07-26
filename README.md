# Endstone BlockData API

[![Version](https://img.shields.io/badge/version-v0.4.5--beta.29-blue.svg?style=for-the-badge)](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/tag/v0.4.5-beta.29)
[![Endstone](https://img.shields.io/badge/Endstone-v0.11.6-emerald.svg?style=for-the-badge)](https://github.com/EndstoneMC/endstone)
[![BDS Version](https://img.shields.io/badge/BDS-1.26.33-purple.svg?style=for-the-badge)](https://www.minecraft.net/en-us/download/server/bedrock)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg?style=for-the-badge)](https://github.com/TheNINJALLO/endstone-blockdata-api/actions)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-orange.svg?style=for-the-badge)](#-direct-release-downloads-v045-beta29)
[![Language](https://img.shields.io/badge/language-C%2B%2B20%20%7C%20Python-3776AB.svg?style=for-the-badge)](#-c--python-api-quickstart)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg?style=for-the-badge)](LICENSE)

A high-performance, detached **Block State**, **Block Entity**, and **Canonical NBT** manipulation API for Endstone Bedrock Dedicated Servers (BDS).

Designed for complex inventory handling, container snapshots, anti-grief transaction diffing, and live block trait modification without risking world corruption or looper thread lockups.

---

## 📚 Documentation & Technical Wiki

Comprehensive guides, architecture diagrams, container audit tutorials, and full API specifications are available on the [**Docsify Documentation Site**](docs/README.md).

---

## 📦 Direct Release Downloads (`v0.4.5-beta.29`)

Use the **complete ZIP** matching the server's exact BDS build and platform when installing the `/bd` wheel; it contains the native plugin and `_endstone_blockdata_live` bridge. The raw library downloads are for C++-only/manual installations and do not contain that bridge.

| Platform | BDS Version | Artifact Filename | Direct Download |
| :--- | :--- | :--- | :--- |
| **Windows x64 ZIP (recommended)** | `1.26.33` | `endstone-blockdata-api-v0.4.5-beta.29-bds-1.26.33-windows-x64.zip` | [Download](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/download/v0.4.5-beta.29/endstone-blockdata-api-v0.4.5-beta.29-bds-1.26.33-windows-x64.zip) |
| **Linux x64 ZIP (recommended)** | `1.26.33` | `endstone-blockdata-api-v0.4.5-beta.29-bds-1.26.33-linux-x64.zip` | [Download](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/download/v0.4.5-beta.29/endstone-blockdata-api-v0.4.5-beta.29-bds-1.26.33-linux-x64.zip) |
| **Windows x64 raw plugin** | `1.26.33` | `endstone-blockdata-api-v0.4.5-beta.29-bds-1.26.33-windows-x64.dll` | [Download](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/download/v0.4.5-beta.29/endstone-blockdata-api-v0.4.5-beta.29-bds-1.26.33-windows-x64.dll) |
| **Linux x64 raw plugin** | `1.26.33` | `endstone-blockdata-api-v0.4.5-beta.29-bds-1.26.33-linux-x64.so` | [Download](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/download/v0.4.5-beta.29/endstone-blockdata-api-v0.4.5-beta.29-bds-1.26.33-linux-x64.so) |
| **Python Wheel** | `CPython 3.12` | `endstone_blockdata_inspector-0.4.5b29-py3-none-any.whl` | [Download](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/download/v0.4.5-beta.29/endstone_blockdata_inspector-0.4.5b29-py3-none-any.whl) |

---

## 🏛️ Architecture Overview

```mermaid
graph TD
    A[Bedrock World / Player Interaction] -->|Capture State| B[BlockDataService]
    B -->|State & NBT Snapshot| C[BlockSnapshot]
    C -->|Construct View| D[ContainerView]
    D -->|NBT Item Modification| E[BlockPatch]
    E -->|Apply with Policy| B
    B -->|Optimistic Revision Check| F[ApplyResult]
    C -->|Diff Engine| G[BlockEntityAuditDelta]
    G -->|Transaction Event| H[Anti-Grief Audit Log]
```

---

## ⚡ Quickstart Code Examples

### Python API Example
```python
from endstone_blockdata import BlockDataService, ContainerView, ConflictPolicy

service = BlockDataService()

# 1. Capture block state & NBT snapshot
snapshot = service.capture("overworld", (100, 64, 200))
print(f"Block: {snapshot.type}, Revision: {snapshot.revision}")

# 2. Inspect & Modify Container NBT
if snapshot.block_entity:
    view = ContainerView(snapshot)
    # Insert custom item with NBT into slot 0
    patch = view.patch_item(0, {
        "id": "minecraft:diamond_sword",
        "count": 1,
        "tag": {"display": {"Name": "§6Excalibur"}}
    })
    result = service.apply(patch, ConflictPolicy.FORCE)
    print(f"Apply Status: {result.status}")
```

### C++ API Example
```cpp
#include <endstone_blockdata/live_service.h>
#include <endstone/endstone.hpp>
#include <string>

void onContainerTouch(endstone::Server &server) {
    using namespace endstone_blockdata;
    auto service = server.getServiceManager().load<LiveBlockDataService>(
        std::string(BlockDataServiceName));
    if (!service) return;  // The native BlockData plugin is not enabled.

    BlockLocation location{"overworld", 100, 64, 200};
    auto snapshot = service->capture(location);
    if (!snapshot) return;

    BlockPatch patch;
    patch.location = location;
    patch.expected_revision = snapshot->revision;
    patch.state_updates["minecraft:cardinal_direction"] = std::string("north");
    auto result = service->apply(patch, ConflictPolicy::FailIfChanged);
    if (!result.ok()) {
        server.getLogger().warning("BlockData apply failed: {}", result.message);
    }
}
```

---

## 🎮 In-Game Inspector Test Suite (`/bd`)

The repository includes a packaged Python wheel test plugin [`endstone_blockdata_inspector`](examples/python/block_data_inspector_plugin/). The wheel and its ABI-tagged native bridge require the Endstone host to run **CPython 3.12**. It calls the exact bundle's `_endstone_blockdata_live` bridge, so expose the extracted bundle's `python/` directory to Endstone before installing the wheel (or copy that directory's contents into Endstone's Python `site-packages`):

```bash
# Use the python/ directory from the same OS and BDS build as the native plugin.
export PYTHONPATH=/path/to/extracted/exact-bundle/python${PYTHONPATH:+:$PYTHONPATH}

# Place the command-test wheel in the Endstone server's plugins/ directory.
cp endstone_blockdata_inspector-0.4.5b29-py3-none-any.whl /path/to/endstone/plugins/
```

### In-Game Command Reference
| Command | Usage | Description |
| :--- | :--- | :--- |
| `/bd locate [radius]` | `/bd locate 10` | Uses native region capture to find live container block entities. |
| `/bd inspect [x] [y] [z]` | `/bd inspect 100 64 200` | Displays live runtime ID, states, revision, actor NBT, and inventory. |
| `/bd item add <slot> <id> [cnt] [nbt]` | `/bd item add 0 diamond 64` | Writes a live item with optimistic revision checking. |
| `/bd item remove <slot>` | `/bd item remove 0` | Clears a live item with optimistic revision checking. |
| `/bd audit <start\|stop\|history>` | `/bd audit start` | Captures and compares live native snapshots. |
| `/bd state set <prop> <val>` | `/bd state set facing south` | Writes a live block-state property. |

---

## 📚 Documentation & Wiki

Full technical documentation, architecture deep dives, and API reference manuals are available in the project Wiki:

- 📖 [Documentation Index](docs/README.md)
- 🏗️ [Architecture & Memory Model](docs/ARCHITECTURE.md)
- 📦 [Canonical NBT & Container Systems](docs/nbt_and_containers.md)
- 🛡️ [Container Transaction Audit Engine](docs/audit_system.md)
- 📘 [Complete API Reference](docs/api_reference.md)
- 💡 [Code Examples & Recipes](examples/python/)

---

## 📜 License

Distributed under the [Apache License 2.0](LICENSE).
