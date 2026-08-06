# Bundle and Storage Item Module

The storage-item module reads and edits the serialized contents of vanilla bundles and custom items that use `minecraft:storage_item`. It only permits edits when the serialized contents are actually present.

It uses the item NBT already captured by BlockData. Bundle contents are stored under:

```text
tag.storage_item_component_content
```

A bundle identifier alone proves that an item is a storage item; it does not prove that its dynamic contents were captured. When the contents field is absent, validation returns `contents_unavailable`, and ordinary `StorageItemView` construction fails instead of interpreting the item as an empty bundle. This prevents an edit from replacing unseen live contents with an empty list.

## What it supports

- Vanilla bundles and colored bundle identifiers
- Custom storage items, including custom backpacks
- Reading, adding, replacing, and removing contained items
- Nested storage items
- Slot-range and duplicate-slot checks
- Configurable allowed and banned item lists
- Vanilla shulker-box rejection
- The 64-point storage weight limit
- Exact or partial weight validation
- Detached editing, followed by a normal optimistic-revision BlockData patch

## Python example

```python
from endstone_blockdata import (
    BlockDataService,
    ContainerView,
    ConflictPolicy,
    LiveBlockDataAdapter,
    StorageItemView,
    validate_storage_item,
    make_max_stack_size_weight_resolver,
)

service = BlockDataService(LiveBlockDataAdapter(self.server))
snapshot = service.capture("overworld", (100, 64, 200))
container = ContainerView(snapshot)

# The bundle is stored in chest slot 4.
bundle_item = container.get_item(4)
if bundle_item is None:
    raise RuntimeError("slot 4 is empty")

captured = validate_storage_item(bundle_item)
if not captured.ok:
    raise RuntimeError(captured.message)

bundle = StorageItemView(bundle_item)
bundle.set_item(0, {
    "Name": "minecraft:diamond",
    "Count": 16,
})

# Exact bundle weight needs item-definition information. A plugin can build
# this resolver from its own registry table or native item metadata.
weights = make_max_stack_size_weight_resolver({
    "minecraft:diamond": 64,
    "minecraft:ender_pearl": 16,
    "minecraft:netherite_sword": 1,
})
validation = bundle.validate(weights)
if not validation.ok:
    raise ValueError(validation.message)

result = service.apply(bundle.patch_parent(snapshot, 4), ConflictPolicy.FAIL_IF_CHANGED)
print(result.status, result.message)
```

## C++ example

```cpp
#include <endstone_blockdata/container.h>
#include <endstone_blockdata/storage_item.h>

using namespace endstone_blockdata;

ContainerView container(snapshot);
auto parent = container.getSlot(4);
if (!parent) return;

auto captured = validateStorageItem(parent->item);
if (!captured.ok()) return;

StorageItemView bundle(parent->item);
bundle.setSlot(0, NbtValue::compound({
    {"Name", std::string("minecraft:diamond")},
    {"Count", std::int8_t(16)},
}));

auto resolver = makeMaxStackSizeWeightResolver(
    [](std::string_view id) -> std::optional<std::int32_t> {
        if (id == "minecraft:diamond") return 64;
        if (id == "minecraft:ender_pearl") return 16;
        if (id == "minecraft:netherite_sword") return 1;
        return std::nullopt;
    });

auto validation = bundle.validate(resolver);
if (!validation.ok()) return;

auto patch = container.patchSlot(4, std::move(bundle).releaseItem());
auto result = service.apply(patch, ConflictPolicy::FailIfChanged);
```

## Explicit creation of an empty serialized storage item

When intentionally authoring a new, known-empty item, pass `create_if_missing=True` in Python or `true` as the third C++ constructor argument. This explicitly initializes `tag.storage_item_component_content` to an empty list:

```python
backpack = StorageItemView(
    {"Name": "ninjos:backpack", "Count": 1},
    create_if_missing=True,
)
```

```cpp
StorageItemView backpack(
    NbtValue::compound({
        {"Name", std::string("ninjos:backpack")},
        {"Count", std::int8_t(1)},
    }),
    {},
    true);
```

The item still needs a valid `minecraft:storage_item` component in its behavior pack. This module edits its serialized contents; it does not register item components with Bedrock.

Do not use `create_if_missing` on a captured live bundle merely because its contents field is absent. That absence means the contents are unavailable, not that the bundle is empty.

## Weight validation

Structural validation works without a resolver. In that case the result may be `weight_unknown`, which means the NBT layout is valid but the module only knows a lower-bound weight.

For exact validation, supply one of these:

- A direct per-item weight resolver
- A max-stack-size resolver using `make_max_stack_size_weight_resolver`
- `_endstone_storage_weight` on a detached item snapshot
- `_endstone_max_stack_size` on a detached item snapshot

Custom storage rules are represented by `StorageItemRules`. They include slot capacity, maximum weight, nested-item weight, nested-storage permission, allowed items, and banned items.

## Unavailable versus empty

These states are intentionally distinct:

- A present `storage_item_component_content: []` list is a serialized empty storage item and validates normally.
- A recognized bundle with no contents field returns `contents_unavailable` and is not valid for editing.
- A contents field with the wrong NBT type returns `invalid_contents`.

The helpers work with item NBT obtained from either block containers or the player-inventory adapter. The exact 1.26.40 block adapter supports live bundle reads and writes with native dynamic-container lifetime transfer. Player bundle contents are readable but live player storage-item writes are deliberately rejected until that owning-inventory lifetime transfer is exposed. Always validate the captured item before constructing an editable view.
