#include "endstone_blockdata/player_inventory.h"
#include "endstone_blockdata/storage_item.h"

#include <algorithm>
#include <cassert>
#include <iostream>
#include <stdexcept>

using namespace endstone_blockdata;

namespace endstone {
class Player {};
}

namespace {

class FakePlayerInventoryAdapter final : public IPlayerInventoryAdapter {
public:
    std::optional<PlayerInventorySnapshot> capture(endstone::Player &) override
    {
        return snapshot;
    }

    ApplyResult apply(
        endstone::Player &,
        const PlayerInventoryPatch &patch,
        ConflictPolicy policy) override
    {
        last_patch = patch;
        last_policy = policy;
        ++apply_calls;
        return {ApplyStatus::Applied, "applied", 999};
    }

    std::string_view name() const noexcept override { return "fake-player-inventory"; }

    PlayerInventorySnapshot snapshot;
    PlayerInventoryPatch last_patch;
    ConflictPolicy last_policy{ConflictPolicy::FailIfChanged};
    int apply_calls{};
};

NbtValue item(std::string name, std::int8_t count = 1)
{
    return NbtValue::compound({
        {"Name", std::move(name)},
        {"Count", count},
    });
}

} // namespace

int main()
{
    PlayerInventorySnapshot snapshot;
    snapshot.player_name = "Josh";
    snapshot.xuid = "1234";
    snapshot.selected_hotbar_slot = 2;
    snapshot.main_size = 36;
    snapshot.armor_size = 4;
    snapshot.offhand_size = 1;
    snapshot.ender_chest_size = 27;

    auto bundle = item("minecraft:bundle");
    StorageItemView bundle_view(bundle, {}, true);
    bundle_view.setSlot(0, item("minecraft:diamond", 3));
    bundle = bundle_view.item();

    snapshot.main.push_back({2, bundle, hashNbt(bundle)});
    snapshot.main.push_back({8, item("minecraft:stone", 64), 0});
    snapshot.main.back().revision = hashNbt(snapshot.main.back().item);
    snapshot.armor.push_back({0, item("minecraft:diamond_helmet"), 0});
    snapshot.armor.back().revision = hashNbt(snapshot.armor.back().item);
    snapshot.offhand.push_back({0, item("minecraft:shield"), 0});
    snapshot.offhand.back().revision = hashNbt(snapshot.offhand.back().item);
    snapshot.revision = calculatePlayerInventoryRevision(snapshot);

    PlayerInventorySnapshot reordered = snapshot;
    std::reverse(reordered.main.begin(), reordered.main.end());
    assert(calculatePlayerInventoryRevision(reordered) == snapshot.revision);

    PlayerInventoryView view(snapshot);
    const auto bundle_slot = view.getItem(PlayerInventorySection::Main, 2);
    assert(bundle_slot.has_value());
    assert(isStorageItemNbt(bundle_slot->item));

    StorageItemView editable(bundle_slot->item);
    editable.setSlot(1, item("minecraft:emerald", 4));
    auto bundle_patch = view.patchItem(PlayerInventorySection::Main, 2, editable.item());
    assert(bundle_patch.expected_revision == snapshot.revision);
    assert(bundle_patch.main_updates.contains(2));

    auto armor_patch = view.patchItem(
        PlayerInventorySection::Armor,
        1,
        item("minecraft:diamond_chestplate"));
    assert(armor_patch.armor_updates.contains(1));

    auto offhand_patch = view.clearItem(PlayerInventorySection::Offhand, 0);
    assert(offhand_patch.offhand_removals.contains(0));

    auto ender_patch = view.patchItem(
        PlayerInventorySection::EnderChest,
        5,
        item("minecraft:gold_ingot", 8));
    assert(ender_patch.ender_chest_updates.contains(5));

    bool threw = false;
    try {
        static_cast<void>(view.patchItem(
            PlayerInventorySection::Armor,
            4,
            item("minecraft:stone")));
    }
    catch (const std::out_of_range &) {
        threw = true;
    }
    assert(threw);

    auto changed = snapshot;
    changed.offhand.clear();
    assert(calculatePlayerInventoryRevision(changed) != snapshot.revision);

    auto fake = std::make_shared<FakePlayerInventoryAdapter>();
    fake->snapshot = snapshot;
    PlayerInventoryService service(fake);
    endstone::Player player;

    PlayerInventoryPatch invalid_offhand;
    invalid_offhand.offhand_removals.insert(1);
    assert(service.apply(player, invalid_offhand).status == ApplyStatus::InvalidPatch);
    assert(fake->apply_calls == 0);

    PlayerInventoryPatch contradictory;
    contradictory.main_updates.emplace(0, PlayerInventoryItemSnapshot{0, item("minecraft:stone"), 0});
    contradictory.main_removals.insert(0);
    assert(service.apply(player, contradictory).status == ApplyStatus::InvalidPatch);
    assert(fake->apply_calls == 0);

    PlayerInventoryPatch valid;
    valid.expected_revision = snapshot.revision;
    valid.main_updates.emplace(1, PlayerInventoryItemSnapshot{1, item("minecraft:diamond"), 0});
    const auto result = service.apply(player, valid, ConflictPolicy::FailIfChanged);
    assert(result.ok());
    assert(fake->apply_calls == 1);
    assert(fake->last_patch.main_updates.contains(1));
    assert(service.adapterName() == "fake-player-inventory");

    assert(service.apply(player, valid, ConflictPolicy::Replace).status == ApplyStatus::Unsupported);
    assert(fake->apply_calls == 1);

    std::cout << "player inventory tests passed\n";
    return 0;
}
