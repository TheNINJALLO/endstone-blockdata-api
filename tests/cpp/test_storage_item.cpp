#include "endstone_blockdata/storage_item.h"

#include <cassert>
#include <iostream>
#include <optional>
#include <stdexcept>
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

    auto unavailable_bundle = makeItem("minecraft:bundle");
    assert(isStorageItemNbt(unavailable_bundle));
    const auto unavailable = validateStorageItem(unavailable_bundle, {}, resolver);
    assert(unavailable.status == StorageItemStatus::ContentsUnavailable);
    assert(storageItemStatusName(unavailable.status) == "contents_unavailable");
    assert(!unavailable.ok());

    bool unavailable_rejected = false;
    try {
        StorageItemView ignored(unavailable_bundle);
    }
    catch (const std::invalid_argument &error) {
        unavailable_rejected =
            std::string_view(error.what()) == "storage item contents are unavailable";
    }
    assert(unavailable_rejected);

    StorageItemView bundle(unavailable_bundle, {}, true);
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

    StorageItemView inner(makeItem("minecraft:bundle"), {}, true);
    inner.setSlot(0, makeItem("minecraft:diamond", 4));
    bundle.setSlot(1, std::move(inner).releaseItem());
    result = bundle.validate(resolver);
    assert(result.status == StorageItemStatus::Valid);
    assert(result.used_weight == 24);

    StorageItemView overweight(makeItem("minecraft:bundle"), {}, true);
    overweight.setSlot(0, makeItem("minecraft:netherite_sword"));
    overweight.setSlot(1, makeItem("minecraft:diamond"));
    assert(overweight.validate(resolver).status == StorageItemStatus::Overweight);

    StorageItemView blocked(makeItem("minecraft:bundle"), {}, true);
    blocked.setSlot(0, makeItem("minecraft:purple_shulker_box"));
    assert(blocked.validate(resolver).status == StorageItemStatus::ForbiddenItem);

    StorageItemRules no_nesting;
    no_nesting.allow_nested_storage_items = false;
    StorageItemView no_nested_bundle(makeItem("minecraft:bundle"), no_nesting, true);
    StorageItemView nested(makeItem("minecraft:bundle"), {}, true);
    no_nested_bundle.setSlot(0, std::move(nested).releaseItem());
    assert(no_nested_bundle.validate(resolver).status == StorageItemStatus::NestedStorageDisabled);

    StorageItemView custom(makeItem("ninjos:backpack"), {}, true);
    custom.setSlot(0, makeItem("minecraft:stone", 64));
    assert(custom.contents().size() == 1);

    auto nested_unavailable = makeItem("minecraft:bundle");
    bundle.setSlot(2, nested_unavailable);
    assert(bundle.validate(resolver).status == StorageItemStatus::ContentsUnavailable);

    auto malformed = NbtValue::compound({
        {"Name", std::string("minecraft:bundle")},
        {"Count", std::int8_t(1)},
        {"tag", std::string("not-a-compound")},
    });
    assert(validateStorageItem(malformed).status == StorageItemStatus::InvalidContents);

    auto boolean_count = NbtValue::compound({
        {"Name", std::string("minecraft:bundle")},
        {"Count", true},
        {"tag", NbtValue::compound({
             {std::string(StorageItemContentsKey), NbtValue::list({})},
         })},
    });
    assert(validateStorageItem(boolean_count).status == StorageItemStatus::InvalidItem);

    auto boolean_slot_bundle = NbtValue::compound({
        {"Name", std::string("minecraft:bundle")},
        {"Count", std::int8_t(1)},
        {"tag", NbtValue::compound({
             {std::string(StorageItemContentsKey), NbtValue::list({
                  NbtValue::compound({
                      {"Slot", false},
                      {"Name", std::string("minecraft:stone")},
                      {"Count", std::int8_t(1)},
                  }),
              })},
         })},
    });
    assert(validateStorageItem(boolean_slot_bundle).status == StorageItemStatus::InvalidContents);

    auto user_data_bundle = NbtValue::compound({
        {"Name", std::string("minecraft:bundle")},
        {"Count", std::int8_t(1)},
        {"user_data", NbtValue::compound({
             {std::string(StorageItemContentsKey), NbtValue::list({})},
         })},
    });
    StorageItemView user_data_view(std::move(user_data_bundle));
    user_data_view.setSlot(0, makeItem("minecraft:stone"));
    assert(user_data_view.contents().size() == 1);

    std::cout << "storage item tests passed\n";
}
