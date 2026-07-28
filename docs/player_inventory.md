# Player Inventory Adapter

The player inventory adapter reads and writes the exact live Bedrock `ItemStack` objects attached to an online player. It uses the same canonical item NBT format as block containers, so bundle and custom `minecraft:storage_item` data is preserved.

## Supported sections

| Section | Slot layout |
|---|---|
| `main` | The player's live main inventory and hotbar. Capacity is reported by BDS. |
| `armor` | `0` head, `1` torso, `2` legs, `3` feet. |
| `offhand` | Slot `0`. |
| `ender_chest` | The player's live Ender Chest container. Capacity is reported by BDS. |

Only occupied slots are returned. The separate size fields preserve the complete capacity of each section.

## Safety model

Player inventory access is enabled only for the exact supported runtime:

- BDS `1.26.33`
- Endstone `0.11.6`
- 64-bit Windows or Linux
- Endstone primary thread

A capture receives a deterministic revision. The normal `fail_if_changed` policy rejects a write when any item in the player's inventory changed after the capture. Every replacement item and every slot is validated before the first live item is changed, so an invalid patch cannot leave a partially updated inventory.

## Python example

```python
from endstone_blockdata import (
    LivePlayerInventoryAdapter,
    PlayerInventorySection,
    PlayerInventoryView,
)

adapter = LivePlayerInventoryAdapter(self.server)
snapshot = adapter.capture(player)
if snapshot is None:
    return

view = PlayerInventoryView(snapshot)

# Read and modify a bundle in main-inventory slot 2.
bundle = view.storage_item(PlayerInventorySection.MAIN, 2)
bundle.set_item(1, {
    "Name": "minecraft:diamond",
    "Count": 4,
})

patch = view.patch_storage_item(PlayerInventorySection.MAIN, 2, bundle)
result = adapter.apply(player, patch)
print(result)
```

## C++ service example

```cpp
#include <endstone_blockdata/live_player_inventory_service.h>
#include <endstone_blockdata/player_inventory.h>
#include <endstone/endstone.hpp>

void inspect(endstone::Server &server, endstone::Player &player) {
    using namespace endstone_blockdata;
    auto service = server.getServiceManager().load<LivePlayerInventoryService>(
        std::string(PlayerInventoryServiceName));
    if (!service) return;

    auto snapshot = service->capture(player);
    if (!snapshot) return;

    PlayerInventoryView view(*snapshot);
    auto item = view.getItem(PlayerInventorySection::Main, 2);
}
```

## Client synchronization

Main inventory and Ender Chest writes use native `Container::setItem` and change notifications. Armor and offhand writes use the player's native equipment setters. The adapter sends a final inventory refresh after the complete patch is applied.

## Offline players

The adapter intentionally works only with online, live players. Offline inventory data is stored in world/player data and requires a separate offline-data adapter with file locking and save coordination. This module does not edit offline player records.
