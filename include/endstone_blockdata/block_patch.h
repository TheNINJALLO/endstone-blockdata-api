#pragma once
#include "endstone_blockdata/block_snapshot.h"
#include <map>
#include <set>

namespace endstone_blockdata {
struct BlockPatch {
    BlockLocation location;
    std::optional<std::uint64_t> expected_revision;
    std::optional<std::string> replacement_type;
    std::map<std::string, BlockStateValue> state_updates;
    std::set<std::string> state_removals;
    std::map<std::string, NbtValue> nbt_updates;
    std::set<std::string> nbt_removals;
    std::map<std::int32_t, InventorySlotSnapshot> inventory_updates;
    std::set<std::int32_t> inventory_removals;
};
}
