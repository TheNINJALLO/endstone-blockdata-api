#pragma once
#include "endstone_blockdata/block_data_service.h"
#include <stdexcept>
#include <vector>

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

enum class ShelfKind {
    Shelf,
    ChiseledBookshelf,
};

// Typed live view for the two vanilla shelf actors. Construction validates
// actor identity, capture completeness, exact capacity, and slot bounds so a
// caller never mistakes a partial or ABI-mismatched capture for an empty shelf.
class ShelfView {
public:
    explicit ShelfView(BlockSnapshot snapshot);

    [[nodiscard]] const BlockSnapshot &snapshot() const noexcept { return snapshot_; }
    [[nodiscard]] ShelfKind kind() const noexcept { return kind_; }
    [[nodiscard]] std::int32_t capacity() const noexcept;
    [[nodiscard]] std::vector<std::optional<InventorySlotSnapshot>> slots() const;
    [[nodiscard]] std::optional<InventorySlotSnapshot> getSlot(std::int32_t slot) const;

    BlockPatch patchSlot(std::int32_t slot, NbtValue item) const;
    BlockPatch clearSlot(std::int32_t slot) const;
    BlockPatch patchSlots(std::map<std::int32_t, NbtValue> updates,
                          std::set<std::int32_t> removals = {}) const;
    BlockPatch replaceSlots(std::vector<std::optional<NbtValue>> contents) const;

private:
    void validateSlot(std::int32_t slot) const;
    void validateItem(const NbtValue &item) const;

    BlockSnapshot snapshot_;
    ShelfKind kind_{};
};
}
