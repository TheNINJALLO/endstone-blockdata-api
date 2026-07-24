#include "endstone_blockdata/adapter.h"
#include <mutex>
#include <unordered_map>

namespace endstone_blockdata {
namespace {
struct KeyHash { size_t operator()(const BlockLocation &l) const noexcept { size_t h=std::hash<std::string>{}(l.dimension); h^=std::hash<int>{}(l.x)+(h<<6)+(h>>2); h^=std::hash<int>{}(l.y)+(h<<6)+(h>>2); h^=std::hash<int>{}(l.z)+(h<<6)+(h>>2); return h; } };

class InMemoryAdapter final : public IBlockAdapter {
public:
    std::string_view name() const noexcept override { return "in-memory"; }
    AdapterCapabilities capabilities() const noexcept override { return {true,true,true,true,true,true}; }
    std::optional<BlockSnapshot> capture(const BlockLocation &l) override {
        std::scoped_lock lock(mu_); auto it=blocks_.find(l); if(it==blocks_.end()) {
            BlockSnapshot air; air.location=l; air.revision=calculateRevision(air); return air;
        } return it->second;
    }
    ApplyResult apply(const BlockPatch &p, ConflictPolicy policy) override {
        std::scoped_lock lock(mu_);
        auto [it, inserted] = blocks_.try_emplace(p.location);
        auto &s = it->second;
        if (inserted) s.location = p.location;
        if(s.type.empty()) s.type="minecraft:air";
        s.revision=calculateRevision(s);
        if(p.expected_revision && policy!=ConflictPolicy::Force && *p.expected_revision!=s.revision)
            return {ApplyStatus::Conflict,"revision changed",s.revision};
        if(p.replacement_type) s.type=*p.replacement_type;
        for(const auto &[k,v]:p.state_updates) s.states[k]=v;
        for(const auto &k:p.state_removals) s.states.erase(k);
        if(!p.nbt_updates.empty() || !p.nbt_removals.empty() || !p.inventory_updates.empty() || !p.inventory_removals.empty()) {
            if(!s.block_entity) s.block_entity=BlockEntitySnapshot{"generic",NbtValue::compound({}),{}};
            auto ptr=std::get_if<NbtValue::CompoundPtr>(&s.block_entity->nbt.value);
            if(!ptr || !*ptr) s.block_entity->nbt=NbtValue::compound({});
            auto compound=std::get<NbtValue::CompoundPtr>(s.block_entity->nbt.value);
            for(const auto &[k,v]:p.nbt_updates) (*compound)[k]=v;
            for(const auto &k:p.nbt_removals) compound->erase(k);
            for(const auto &slot:p.inventory_removals) std::erase_if(s.block_entity->inventory,[&](const auto &x){return x.slot==slot;});
            for(const auto &[slot,val]:p.inventory_updates){ std::erase_if(s.block_entity->inventory,[&](const auto &x){return x.slot==slot;}); s.block_entity->inventory.push_back(val); }
        }
        s.revision=calculateRevision(s);
        return {ApplyStatus::Applied,"applied",s.revision};
    }
private:
    std::mutex mu_;
    std::unordered_map<BlockLocation,BlockSnapshot,KeyHash> blocks_;
};
}
std::shared_ptr<IBlockAdapter> makeInMemoryAdapter(){ return std::make_shared<InMemoryAdapter>(); }
}
