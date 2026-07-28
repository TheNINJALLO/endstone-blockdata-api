#include "endstone_blockdata/storage_item.h"

#include <cassert>
#include <iostream>
#include <optional>
#include <string>
#include <string_view>

using namespace endstone_blockdata;

namespace {
NbtValue makeItem(std::string identifier, std::int32_t count = 1)
{
    return NbtValue::compound({
        {"Name", std::move(identifier)},
        {"Count", static_cast<std::int8_t>(count)},
    });
}
}

int main()
{
    auto resolver = makeMaxStackSizeWeightResolver(
        [](std::string_view identifier) -> std::optional<std::int32_t> {
            if (identifier == "minecraft:diamond" || identifier == "minecraft:stone") return 64;
            if (identifier == "minecraft:ender_pearl") return 16;
            if (identifier == "minecraft:netherite_sword") return 1;
            return std::nullopt;
        });

    StorageItemView bundle(makeItem("minecraft:bundle"));
    assert(bundle.contents().empty());
    bundle.setSlot(0, makeItem("minecraft:diamond", 16));
    bundle.setSlot(3, makeItem("minecraft:ender_pearl", 4));
    auto result = bundle.validate(resolver);
    assert(result.status == StorageItemStatus::Valid);
    assert(result.exact_weight);
    assert(result.used_weight == 32);
    assert(bundle.getSlot(3));
    bundle.clearSlot(3);
    assert(!bundle.getSlot(3));

    StorageItemView inner(makeItem("minecraft:bundle"));
    inner.setSlot(0, makeItem("minecraft:diamond", 4));
    bundle.setSlot(1, std::move(inner).releaseItem());
    result = bundle.validate(resolver);
    assert(result.status == StorageItemStatus::Valid);
    assert(result.used_weight == 24);

    StorageItemView overweight(makeItem("minecraft:bundle"));
    overweight.setSlot(0, makeItem("minecraft:netherite_sword"));
    overweight.setSlot(1, makeItem("minecraft:diamond"));
    assert(overweight.validate(resolver).status == StorageItemStatus::Overweight);

    StorageItemView blocked(makeItem("minecraft:bundle"));
    blocked.setSlot(0, makeItem("minecraft:purple_shulker_box"));
    assert(blocked.validate(resolver).status == StorageItemStatus::ForbiddenItem);

    StorageItemRules no_nesting;
    no_nesting.allow_nested_storage_items = false;
    StorageItemView no_nested_bundle(makeItem("minecraft:bundle"), no_nesting);
    StorageItemView nested(makeItem("minecraft:bundle"));
    no_nested_bundle.setSlot(0, std::move(nested).releaseItem());
    assert(no_nested_bundle.validate(resolver).status == StorageItemStatus::NestedStorageDisabled);

    StorageItemView custom(makeItem("ninjos:backpack"), {}, true);
    custom.setSlot(0, makeItem("minecraft:stone", 64));
    assert(custom.contents().size() == 1);

    std::cout << "storage item tests passed\n";
}
