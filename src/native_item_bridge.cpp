#include "native_item_bridge.h"

#include "bedrock/world/item/item_stack_base.h"
#include "bedrock/world/item/registry/item_registry_manager.h"
#include "bedrock/world/level/level.h"

#include <utility>
#include <vector>

namespace {
thread_local Level *active_item_registry_level = nullptr;
}

namespace endstone_blockdata {

NativeItemRegistryScope::NativeItemRegistryScope(Level &level) noexcept
    : previous_(std::exchange(active_item_registry_level, &level))
{
}

NativeItemRegistryScope::~NativeItemRegistryScope() noexcept
{
    active_item_registry_level = previous_;
}

} // namespace endstone_blockdata

ItemRegistryRef ItemRegistryManager::getItemRegistry()
{
    static const ItemRegistryRef invalid;
    return active_item_registry_level ? active_item_registry_level->getItemRegistry() : invalid;
}

bool ItemStackBase::setCanPlaceOn(const std::vector<std::string> &block_ids)
{
    std::vector<const BlockType *> resolved;
    resolved.reserve(block_ids.size());
    for (const auto &block_id : block_ids) {
        if (!_loadBlocksForCanPlaceOnCanDestroy(resolved, block_id)) return false;
    }
    can_place_on_ = std::move(resolved);
    _updateCompareHashes();
    return true;
}

bool ItemStackBase::setCanDestroy(const std::vector<std::string> &block_ids)
{
    std::vector<const BlockType *> resolved;
    resolved.reserve(block_ids.size());
    for (const auto &block_id : block_ids) {
        if (!_loadBlocksForCanPlaceOnCanDestroy(resolved, block_id)) return false;
    }
    can_destroy_ = std::move(resolved);
    _updateCompareHashes();
    return true;
}
