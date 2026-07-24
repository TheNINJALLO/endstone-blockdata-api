#pragma once
#include "endstone_blockdata/nbt.h"
#include "endstone_blockdata/types.h"
#include <optional>

namespace endstone_blockdata {
struct InventorySlotSnapshot {
    std::int32_t slot{};
    NbtValue item;
    std::uint64_t revision{};
};

struct BlockEntitySnapshot {
    std::string type;
    // Canonical live block-actor NBT projection. For containers this includes
    // id/x/y/z, custom name, additional save data and a complete Items list.
    NbtValue nbt{NbtValue::compound({})};
    std::string raw_snbt;
    bool canonical_nbt{};
    std::vector<InventorySlotSnapshot> inventory;
};

struct BlockSnapshot {
    BlockLocation location;
    std::string type{"minecraft:air"};
    std::uint32_t runtime_id{};
    BlockStates states;
    std::optional<BlockEntitySnapshot> block_entity;
    std::uint64_t revision{};
};

std::uint64_t calculateRevision(const BlockSnapshot &snapshot);
}
