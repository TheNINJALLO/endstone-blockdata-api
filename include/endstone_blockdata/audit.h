#pragma once
#include "endstone_blockdata/block_snapshot.h"
#include <optional>
#include <string>
#include <vector>

namespace endstone_blockdata {
enum class InventoryChangeKind { Added, Removed, Changed };

struct InventoryChange {
    std::int32_t slot{};
    InventoryChangeKind kind{InventoryChangeKind::Changed};
    std::optional<NbtValue> before;
    std::optional<NbtValue> after;
};

struct BlockEntityAuditDelta {
    BlockLocation location;
    std::uint64_t before_revision{};
    std::uint64_t after_revision{};
    bool block_changed{};
    bool actor_nbt_changed{};
    std::vector<InventoryChange> inventory_changes;
    [[nodiscard]] bool empty() const noexcept {
        return !block_changed && !actor_nbt_changed && inventory_changes.empty();
    }
};

[[nodiscard]] BlockEntityAuditDelta diffSnapshots(const BlockSnapshot &before, const BlockSnapshot &after);
[[nodiscard]] std::string inventoryChangeKindName(InventoryChangeKind kind);
}
