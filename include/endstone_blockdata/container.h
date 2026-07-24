#pragma once
#include "endstone_blockdata/block_data_service.h"
#include <stdexcept>

namespace endstone_blockdata {
class ContainerView {
public:
    explicit ContainerView(BlockSnapshot snapshot) : snapshot_(std::move(snapshot)) {
        if (!snapshot_.block_entity) throw std::invalid_argument("block has no block entity");
    }
    [[nodiscard]] const BlockSnapshot &snapshot() const noexcept { return snapshot_; }
    [[nodiscard]] std::optional<InventorySlotSnapshot> getSlot(std::int32_t slot) const;
    BlockPatch patchSlot(std::int32_t slot, NbtValue item) const;
    BlockPatch clearSlot(std::int32_t slot) const;
private:
    BlockSnapshot snapshot_;
};
}
