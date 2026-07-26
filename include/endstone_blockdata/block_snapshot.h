#pragma once
#include "endstone_blockdata/nbt.h"
#include "endstone_blockdata/types.h"
#include <optional>
#include <string_view>

namespace endstone_blockdata {
enum class BlockEntityCaptureStatus {
    NotSupported,
    DimensionUnavailable,
    NoActor,
    UnsupportedActor,
    ComponentMismatch,
    ContainerUnavailable,
    Captured,
};

[[nodiscard]] constexpr std::string_view blockEntityCaptureStatusName(
    BlockEntityCaptureStatus status) noexcept {
    switch (status) {
    case BlockEntityCaptureStatus::NotSupported: return "not_supported";
    case BlockEntityCaptureStatus::DimensionUnavailable: return "dimension_unavailable";
    case BlockEntityCaptureStatus::NoActor: return "no_actor";
    case BlockEntityCaptureStatus::UnsupportedActor: return "unsupported_actor";
    case BlockEntityCaptureStatus::ComponentMismatch: return "component_mismatch";
    case BlockEntityCaptureStatus::ContainerUnavailable: return "container_unavailable";
    case BlockEntityCaptureStatus::Captured: return "captured";
    }
    return "not_supported";
}

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
    bool is_container{};
    std::int32_t container_size{};
    // Occupied slots only. container_size preserves the full live capacity.
    std::vector<InventorySlotSnapshot> inventory;
};

struct BlockSnapshot {
    BlockLocation location;
    std::string type{"minecraft:air"};
    std::uint32_t runtime_id{};
    BlockStates states;
    std::optional<BlockEntitySnapshot> block_entity;
    BlockEntityCaptureStatus block_entity_status{BlockEntityCaptureStatus::NotSupported};
    std::uint64_t revision{};
};

std::uint64_t calculateRevision(const BlockSnapshot &snapshot);
}
