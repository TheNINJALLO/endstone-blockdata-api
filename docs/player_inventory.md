# Player Inventory Adapter

The player inventory adapter reads and writes ordinary live Bedrock `ItemStack` objects attached to an online player. It uses the same canonical item NBT format as block containers. Storage-item helpers expose bundle contents when the captured item includes a serialized `storage_item_component_content` list; a bundle identifier without that payload is reported as `contents_unavailable`.

Player bundle/storage-item contents are currently **read-only**. Bedrock assigns their dynamic-container lifetimes to the owning native inventory, while Endstone's public player-inventory setters do not expose that lifetime transfer. The live adapter therefore rejects storage-item replacements instead of accepting a write that could lose contents or leave a dangling container. Block-container bundle reads and writes are supported by the exact BlockData adapter.

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
    validate_storage_item,
)

adapter = LivePlayerInventoryAdapter(self.server)
snapshot = adapter.capture(player)
if snapshot is None:
    return

view = PlayerInventoryView(snapshot)

# Read a bundle in main-inventory slot 2.
item = view.get_item(PlayerInventorySection.MAIN, 2)
if item is None:
    return
captured = validate_storage_item(item)
if not captured.ok:
    raise RuntimeError(captured.message)

bundle = view.storage_item(PlayerInventorySection.MAIN, 2)
for entry in bundle.contents:
    print(entry)
```

Do not pass `create_if_missing=True` for a captured player item whose contents are unavailable. That option is reserved for intentionally authoring a new, known-empty serialized storage item.

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

## Writes and client synchronization

Ordinary main-inventory and Ender Chest writes use Endstone's inventory setters. Armor and offhand writes use the corresponding public equipment setters. Storage-item updates are rejected with `unsupported`; edit a bundle stored in a block container through `BlockDataService` when live contents must be changed.

## Offline players

The adapter intentionally works only with online, live players. Offline inventory data is stored in world/player data and requires a separate offline-data adapter with file locking and save coordination. This module does not edit offline player records.
