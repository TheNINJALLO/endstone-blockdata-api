#pragma once
#include "endstone_blockdata/block_patch.h"
#include <memory>
#include <string_view>

namespace endstone_blockdata {
struct AdapterCapabilities {
    bool block_states{};
    bool block_writes{};
    bool block_entity_nbt{};       // structured canonical block-actor NBT is readable
    bool block_entity_nbt_write{}; // supported fields can be applied to a live block actor
    bool canonical_actor_nbt{};    // live projection rather than a byte-identical hidden BDS save call
    bool item_user_nbt{};          // nested item tag data is exposed for every container slot
    bool inventory{};
    bool mark_dirty{};
    bool client_updates{};
    bool block_entity_metadata{};
    bool container_save_nbt{};     // Container::addAdditionalSaveData included in canonical NBT
    bool raw_block_entity_nbt{};   // byte-identical full actor save/load through hidden BDS ABI
};

class IBlockAdapter {
public:
    virtual ~IBlockAdapter() = default;
    [[nodiscard]] virtual std::string_view name() const noexcept = 0;
    [[nodiscard]] virtual AdapterCapabilities capabilities() const noexcept = 0;
    [[nodiscard]] virtual std::optional<BlockSnapshot> capture(const BlockLocation &location) = 0;
    virtual ApplyResult apply(const BlockPatch &patch, ConflictPolicy policy) = 0;
};

std::shared_ptr<IBlockAdapter> makeInMemoryAdapter();
}
