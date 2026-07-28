#pragma once

#include "endstone_blockdata/nbt.h"
#include "endstone_blockdata/types.h"

#include <cstdint>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <string>
#include <string_view>
#include <vector>

namespace endstone {
class Player;
}

namespace endstone_blockdata {

enum class PlayerInventorySection {
    Main,
    Armor,
    Offhand,
    EnderChest,
};

[[nodiscard]] constexpr std::string_view playerInventorySectionName(
    PlayerInventorySection section) noexcept
{
    switch (section) {
    case PlayerInventorySection::Main: return "main";
    case PlayerInventorySection::Armor: return "armor";
    case PlayerInventorySection::Offhand: return "offhand";
    case PlayerInventorySection::EnderChest: return "ender_chest";
    }
    return "main";
}

struct PlayerInventoryItemSnapshot {
    std::int32_t slot{};
    NbtValue item;
    std::uint64_t revision{};
};

struct PlayerInventorySnapshot {
    std::string player_name;
    std::string xuid;
    std::int32_t selected_hotbar_slot{};
    std::int32_t main_size{};
    std::int32_t armor_size{4};
    std::int32_t offhand_size{1};
    std::int32_t ender_chest_size{};
    std::vector<PlayerInventoryItemSnapshot> main;
    std::vector<PlayerInventoryItemSnapshot> armor;
    std::vector<PlayerInventoryItemSnapshot> offhand;
    std::vector<PlayerInventoryItemSnapshot> ender_chest;
    std::uint64_t revision{};
};

struct PlayerInventoryPatch {
    std::optional<std::uint64_t> expected_revision;
    std::map<std::int32_t, PlayerInventoryItemSnapshot> main_updates;
    std::set<std::int32_t> main_removals;
    std::map<std::int32_t, PlayerInventoryItemSnapshot> armor_updates;
    std::set<std::int32_t> armor_removals;
    std::map<std::int32_t, PlayerInventoryItemSnapshot> offhand_updates;
    std::set<std::int32_t> offhand_removals;
    std::map<std::int32_t, PlayerInventoryItemSnapshot> ender_chest_updates;
    std::set<std::int32_t> ender_chest_removals;
};

[[nodiscard]] std::uint64_t calculatePlayerInventoryRevision(
    const PlayerInventorySnapshot &snapshot);

class IPlayerInventoryAdapter {
public:
    virtual ~IPlayerInventoryAdapter() = default;
    [[nodiscard]] virtual std::optional<PlayerInventorySnapshot> capture(
        endstone::Player &player) = 0;
    virtual ApplyResult apply(
        endstone::Player &player,
        const PlayerInventoryPatch &patch,
        ConflictPolicy policy) = 0;
    [[nodiscard]] virtual std::string_view name() const noexcept = 0;
};

class PlayerInventoryService {
public:
    explicit PlayerInventoryService(std::shared_ptr<IPlayerInventoryAdapter> adapter);

    [[nodiscard]] std::optional<PlayerInventorySnapshot> capture(endstone::Player &player);
    ApplyResult apply(
        endstone::Player &player,
        const PlayerInventoryPatch &patch,
        ConflictPolicy policy = ConflictPolicy::FailIfChanged);
    [[nodiscard]] std::string adapterName() const;

private:
    std::shared_ptr<IPlayerInventoryAdapter> adapter_;
};

class PlayerInventoryView {
public:
    explicit PlayerInventoryView(PlayerInventorySnapshot snapshot);

    [[nodiscard]] const PlayerInventorySnapshot &snapshot() const noexcept { return snapshot_; }
    [[nodiscard]] std::optional<PlayerInventoryItemSnapshot> getItem(
        PlayerInventorySection section,
        std::int32_t slot) const;
    [[nodiscard]] PlayerInventoryPatch patchItem(
        PlayerInventorySection section,
        std::int32_t slot,
        NbtValue item) const;
    [[nodiscard]] PlayerInventoryPatch clearItem(
        PlayerInventorySection section,
        std::int32_t slot) const;

private:
    PlayerInventorySnapshot snapshot_;
};

} // namespace endstone_blockdata
