#include "endstone_blockdata/audit.h"
#include "endstone_blockdata/nbt.h"
#include <map>
#include <stdexcept>

namespace endstone_blockdata {
std::string inventoryChangeKindName(InventoryChangeKind kind) {
    switch (kind) {
    case InventoryChangeKind::Added: return "added";
    case InventoryChangeKind::Removed: return "removed";
    case InventoryChangeKind::Changed: return "changed";
    }
    return "changed";
}

BlockEntityAuditDelta diffSnapshots(const BlockSnapshot &before, const BlockSnapshot &after) {
    if (before.location != after.location) throw std::invalid_argument("snapshot locations differ");
    BlockEntityAuditDelta out;
    out.location = before.location;
    out.before_revision = before.revision;
    out.after_revision = after.revision;
    out.block_changed = before.type != after.type || before.runtime_id != after.runtime_id || before.states != after.states;

    if (before.block_entity.has_value() != after.block_entity.has_value()) {
        out.actor_nbt_changed = true;
    } else if (before.block_entity && after.block_entity) {
        out.actor_nbt_changed = before.block_entity->type != after.block_entity->type ||
                                !nbtEqual(before.block_entity->nbt, after.block_entity->nbt);
    }

    std::map<std::int32_t, NbtValue> left;
    std::map<std::int32_t, NbtValue> right;
    if (before.block_entity) for (const auto &slot : before.block_entity->inventory) left.emplace(slot.slot, slot.item);
    if (after.block_entity) for (const auto &slot : after.block_entity->inventory) right.emplace(slot.slot, slot.item);

    for (const auto &[slot, item] : left) {
        auto found = right.find(slot);
        if (found == right.end()) {
            out.inventory_changes.push_back({slot, InventoryChangeKind::Removed, item, std::nullopt});
        } else if (!nbtEqual(item, found->second)) {
            out.inventory_changes.push_back({slot, InventoryChangeKind::Changed, item, found->second});
        }
    }
    for (const auto &[slot, item] : right) {
        if (!left.contains(slot)) out.inventory_changes.push_back({slot, InventoryChangeKind::Added, std::nullopt, item});
    }
    return out;
}
}
