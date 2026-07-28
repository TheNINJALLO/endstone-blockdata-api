#include "endstone_blockdata/player_inventory.h"

#include <algorithm>
#include <functional>
#include <ranges>
#include <stdexcept>
#include <type_traits>
#include <utility>

namespace endstone_blockdata {
namespace {

void mix(std::uint64_t &hash, std::uint64_t value)
{
    hash ^= value + 0x9e3779b97f4a7c15ULL + (hash << 6U) + (hash >> 2U);
}

const std::vector<PlayerInventoryItemSnapshot> &itemsFor(
    const PlayerInventorySnapshot &snapshot,
    PlayerInventorySection section)
{
    switch (section) {
    case PlayerInventorySection::Main: return snapshot.main;
    case PlayerInventorySection::Armor: return snapshot.armor;
    case PlayerInventorySection::Offhand: return snapshot.offhand;
    case PlayerInventorySection::EnderChest: return snapshot.ender_chest;
    }
    return snapshot.main;
}

std::int32_t capacityFor(
    const PlayerInventorySnapshot &snapshot,
    PlayerInventorySection section)
{
    switch (section) {
    case PlayerInventorySection::Main: return snapshot.main_size;
    case PlayerInventorySection::Armor: return snapshot.armor_size;
    case PlayerInventorySection::Offhand: return snapshot.offhand_size;
    case PlayerInventorySection::EnderChest: return snapshot.ender_chest_size;
    }
    return 0;
}

std::map<std::int32_t, PlayerInventoryItemSnapshot> &updatesFor(
    PlayerInventoryPatch &patch,
    PlayerInventorySection section)
{
    switch (section) {
    case PlayerInventorySection::Main: return patch.main_updates;
    case PlayerInventorySection::Armor: return patch.armor_updates;
    case PlayerInventorySection::Offhand: return patch.offhand_updates;
    case PlayerInventorySection::EnderChest: return patch.ender_chest_updates;
    }
    return patch.main_updates;
}

std::set<std::int32_t> &removalsFor(
    PlayerInventoryPatch &patch,
    PlayerInventorySection section)
{
    switch (section) {
    case PlayerInventorySection::Main: return patch.main_removals;
    case PlayerInventorySection::Armor: return patch.armor_removals;
    case PlayerInventorySection::Offhand: return patch.offhand_removals;
    case PlayerInventorySection::EnderChest: return patch.ender_chest_removals;
    }
    return patch.main_removals;
}

ApplyResult validateSection(
    std::string_view name,
    const std::map<std::int32_t, PlayerInventoryItemSnapshot> &updates,
    const std::set<std::int32_t> &removals)
{
    std::string error;
    for (const auto &[slot, item] : updates) {
        if (slot < 0) {
            return {ApplyStatus::InvalidPatch,
                    std::string(name) + " update slot must be non-negative", 0};
        }
        if (removals.contains(slot)) {
            return {ApplyStatus::InvalidPatch,
                    std::string(name) + " slot cannot be updated and removed in one patch", 0};
        }
        if (!validateNbtPayload(item.item, &error)) {
            return {ApplyStatus::InvalidPatch,
                    "invalid " + std::string(name) + " item at slot " +
                        std::to_string(slot) + ": " + error,
                    0};
        }
    }
    if (std::ranges::any_of(removals, [](std::int32_t slot) { return slot < 0; })) {
        return {ApplyStatus::InvalidPatch,
                std::string(name) + " removal slot must be non-negative", 0};
    }
    return {ApplyStatus::Applied, "valid", 0};
}

} // namespace

std::uint64_t calculatePlayerInventoryRevision(const PlayerInventorySnapshot &snapshot)
{
    std::uint64_t hash = std::hash<std::string>{}(snapshot.xuid);
    mix(hash, std::hash<std::string>{}(snapshot.player_name));
    mix(hash, static_cast<std::uint64_t>(snapshot.selected_hotbar_slot));
    mix(hash, static_cast<std::uint64_t>(snapshot.main_size));
    mix(hash, static_cast<std::uint64_t>(snapshot.armor_size));
    mix(hash, static_cast<std::uint64_t>(snapshot.offhand_size));
    mix(hash, static_cast<std::uint64_t>(snapshot.ender_chest_size));

    const auto mix_section = [&hash](
                                 PlayerInventorySection section,
                                 const std::vector<PlayerInventoryItemSnapshot> &items) {
        mix(hash, static_cast<std::uint64_t>(section));
        std::vector<std::pair<std::int32_t, std::uint64_t>> ordered;
        ordered.reserve(items.size());
        for (const auto &entry : items) {
            ordered.emplace_back(entry.slot, hashNbt(entry.item));
        }
        std::sort(ordered.begin(), ordered.end());
        for (const auto &[slot, revision] : ordered) {
            mix(hash, static_cast<std::uint64_t>(static_cast<std::int64_t>(slot)));
            mix(hash, revision);
        }
    };

    mix_section(PlayerInventorySection::Main, snapshot.main);
    mix_section(PlayerInventorySection::Armor, snapshot.armor);
    mix_section(PlayerInventorySection::Offhand, snapshot.offhand);
    mix_section(PlayerInventorySection::EnderChest, snapshot.ender_chest);
    return hash;
}

PlayerInventoryService::PlayerInventoryService(
    std::shared_ptr<IPlayerInventoryAdapter> adapter)
    : adapter_(std::move(adapter))
{
    if (!adapter_) throw std::invalid_argument("player inventory adapter must not be null");
}

std::optional<PlayerInventorySnapshot> PlayerInventoryService::capture(
    endstone::Player &player)
{
    return adapter_->capture(player);
}

ApplyResult PlayerInventoryService::apply(
    endstone::Player &player,
    const PlayerInventoryPatch &patch,
    ConflictPolicy policy)
{
    if (policy != ConflictPolicy::FailIfChanged && policy != ConflictPolicy::Force) {
        return {ApplyStatus::Unsupported,
                "player inventory supports only FailIfChanged and Force", 0};
    }

    for (const auto &[name, result] : std::initializer_list<std::pair<std::string_view, ApplyResult>>{
             {"main", validateSection("main", patch.main_updates, patch.main_removals)},
             {"armor", validateSection("armor", patch.armor_updates, patch.armor_removals)},
             {"offhand", validateSection("offhand", patch.offhand_updates, patch.offhand_removals)},
             {"ender chest", validateSection("ender chest", patch.ender_chest_updates,
                                              patch.ender_chest_removals)},
         }) {
        static_cast<void>(name);
        if (!result.ok()) return result;
    }

    if (patch.offhand_updates.size() > 1 ||
        (!patch.offhand_updates.empty() && !patch.offhand_updates.contains(0)) ||
        std::ranges::any_of(patch.offhand_removals, [](std::int32_t slot) { return slot != 0; })) {
        return {ApplyStatus::InvalidPatch, "offhand supports only slot 0", 0};
    }

    return adapter_->apply(player, patch, policy);
}

std::string PlayerInventoryService::adapterName() const
{
    return std::string(adapter_->name());
}

PlayerInventoryView::PlayerInventoryView(PlayerInventorySnapshot snapshot)
    : snapshot_(std::move(snapshot))
{
}

std::optional<PlayerInventoryItemSnapshot> PlayerInventoryView::getItem(
    PlayerInventorySection section,
    std::int32_t slot) const
{
    if (slot < 0 || slot >= capacityFor(snapshot_, section)) return std::nullopt;
    const auto &items = itemsFor(snapshot_, section);
    for (const auto &entry : items) {
        if (entry.slot == slot) return entry;
    }
    return std::nullopt;
}

PlayerInventoryPatch PlayerInventoryView::patchItem(
    PlayerInventorySection section,
    std::int32_t slot,
    NbtValue item) const
{
    if (slot < 0 || slot >= capacityFor(snapshot_, section)) {
        throw std::out_of_range("player inventory slot is outside the section capacity");
    }
    PlayerInventoryPatch patch;
    patch.expected_revision = snapshot_.revision;
    const auto current = getItem(section, slot);
    updatesFor(patch, section).emplace(
        slot,
        PlayerInventoryItemSnapshot{slot, std::move(item), current ? current->revision : 0});
    return patch;
}

PlayerInventoryPatch PlayerInventoryView::clearItem(
    PlayerInventorySection section,
    std::int32_t slot) const
{
    if (slot < 0 || slot >= capacityFor(snapshot_, section)) {
        throw std::out_of_range("player inventory slot is outside the section capacity");
    }
    PlayerInventoryPatch patch;
    patch.expected_revision = snapshot_.revision;
    removalsFor(patch, section).insert(slot);
    return patch;
}

} // namespace endstone_blockdata
