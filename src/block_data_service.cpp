#include "endstone_blockdata/block_data_service.h"
#include "endstone_blockdata/container.h"
#include <algorithm>

namespace endstone_blockdata {
namespace {
void mix(std::uint64_t &h, std::uint64_t v) { h ^= v + 0x9e3779b97f4a7c15ULL + (h << 6) + (h >> 2); }
std::uint64_t hashState(const BlockStateValue &v) {
    return std::visit([](const auto &x)->std::uint64_t { return std::hash<std::decay_t<decltype(x)>>{}(x); }, v);
}
}
std::uint64_t calculateRevision(const BlockSnapshot &s) {
    std::uint64_t h = std::hash<std::string>{}(s.type);
    mix(h, s.runtime_id);
    std::vector<std::string> keys; keys.reserve(s.states.size());
    for (const auto &[k,_] : s.states) keys.push_back(k);
    std::sort(keys.begin(), keys.end());
    for (const auto &k : keys) { mix(h, std::hash<std::string>{}(k)); mix(h, hashState(s.states.at(k))); }
    if (s.block_entity) {
        mix(h, std::hash<std::string>{}(s.block_entity->type));
        mix(h, hashNbt(s.block_entity->nbt));
        for (const auto &slot : s.block_entity->inventory) { mix(h, slot.slot); mix(h, hashNbt(slot.item)); }
    }
    return h;
}

BlockDataService::BlockDataService(std::shared_ptr<IBlockAdapter> adapter) : adapter_(std::move(adapter)) {
    if (!adapter_) throw std::invalid_argument("adapter must not be null");
}
std::optional<BlockSnapshot> BlockDataService::capture(const BlockLocation &l) { return adapter_->capture(l); }
std::vector<BlockSnapshot> BlockDataService::captureRegion(const BlockRegion &r) {
    if (r.minimum.dimension != r.maximum.dimension) throw std::invalid_argument("region dimensions differ");
    std::vector<BlockSnapshot> out;
    for (int x=std::min(r.minimum.x,r.maximum.x); x<=std::max(r.minimum.x,r.maximum.x); ++x)
      for (int y=std::min(r.minimum.y,r.maximum.y); y<=std::max(r.minimum.y,r.maximum.y); ++y)
        for (int z=std::min(r.minimum.z,r.maximum.z); z<=std::max(r.minimum.z,r.maximum.z); ++z) {
            auto s=capture({r.minimum.dimension,x,y,z}); if(s) out.push_back(std::move(*s));
        }
    return out;
}
ApplyResult BlockDataService::apply(const BlockPatch &p, ConflictPolicy policy) { return adapter_->apply(p, policy); }
AdapterCapabilities BlockDataService::capabilities() const noexcept { return adapter_->capabilities(); }
std::string BlockDataService::adapterName() const { return std::string(adapter_->name()); }
std::vector<ApplyResult> BlockTransaction::commit(ConflictPolicy policy) {
    std::vector<ApplyResult> results; results.reserve(patches_.size());
    for (const auto &p : patches_) { auto r=service_.apply(p,policy); results.push_back(r); if(!r.ok() && policy!=ConflictPolicy::Force) break; }
    return results;
}
std::optional<InventorySlotSnapshot> ContainerView::getSlot(std::int32_t slot) const {
    for(const auto &s:snapshot_.block_entity->inventory) if(s.slot==slot) return s; return std::nullopt;
}
BlockPatch ContainerView::patchSlot(std::int32_t slot, NbtValue item) const {
    BlockPatch p; p.location=snapshot_.location; p.expected_revision=snapshot_.revision;
    p.inventory_updates[slot]={slot,std::move(item),0}; return p;
}
BlockPatch ContainerView::clearSlot(std::int32_t slot) const {
    BlockPatch p; p.location=snapshot_.location; p.expected_revision=snapshot_.revision; p.inventory_removals.insert(slot); return p;
}
}
