#include <format>
#ifndef format_context
#define format_context std::format_context
#endif

#include "endstone_blockdata/endstone_adapter.h"
#include <endstone/endstone.hpp>
#include <exception>

namespace endstone_blockdata {
namespace {
class EndstonePublicAdapter final : public IBlockAdapter {
public:
    explicit EndstonePublicAdapter(endstone::Server &server) : server_(server) {}
    std::string_view name() const noexcept override { return "endstone-public"; }
    AdapterCapabilities capabilities() const noexcept override { return {true, true, false, false, false, false, false, false, false}; }

    std::optional<BlockSnapshot> capture(const BlockLocation &location) override {
        if (!server_.isPrimaryThread()) return std::nullopt;
        auto *level = server_.getLevel();
        if (!level) return std::nullopt;
        auto *dimension = level->getDimension(location.dimension);
        if (!dimension) return std::nullopt;
        auto block = dimension->getBlockAt(location.x, location.y, location.z);
        if (!block) return std::nullopt;
        auto data = block->getData();
        if (!data) return std::nullopt;
        BlockSnapshot snapshot;
        snapshot.location = location;
        snapshot.type = data->getType();
        snapshot.runtime_id = data->getRuntimeId();
        for (const auto &[key, value] : data->getBlockStates()) {
            std::visit([&](const auto &v) { snapshot.states[key] = v; }, value);
        }
        snapshot.revision = calculateRevision(snapshot);
        return snapshot;
    }

    ApplyResult apply(const BlockPatch &patch, ConflictPolicy policy) override {
        if (!server_.isPrimaryThread()) return {ApplyStatus::AdapterError, "live apply must run on the primary thread", 0};
        if (!patch.nbt_updates.empty() || !patch.nbt_removals.empty() || !patch.inventory_updates.empty() || !patch.inventory_removals.empty())
            return {ApplyStatus::Unsupported, "block-entity NBT requires a verified native adapter", 0};
        auto current = capture(patch.location);
        if (!current) return {ApplyStatus::ChunkUnavailable, "dimension, chunk, or block unavailable", 0};
        if (patch.expected_revision && policy != ConflictPolicy::Force && *patch.expected_revision != current->revision)
            return {ApplyStatus::Conflict, "revision changed", current->revision};
        auto *level = server_.getLevel();
        auto *dimension = level ? level->getDimension(patch.location.dimension) : nullptr;
        if (!dimension) return {ApplyStatus::ChunkUnavailable, "dimension unavailable", current->revision};
        auto block = dimension->getBlockAt(patch.location.x, patch.location.y, patch.location.z);
        if (!block) return {ApplyStatus::ChunkUnavailable, "block unavailable", current->revision};
        try {
            auto type = patch.replacement_type.value_or(current->type);
            auto states = current->states;
            for (const auto &[key, value] : patch.state_updates) states[key] = value;
            for (const auto &key : patch.state_removals) states.erase(key);
            endstone::BlockStates native_states;
            for (const auto &[key, value] : states) std::visit([&](const auto &v) { native_states[key] = v; }, value);
            auto data = server_.createBlockData(type, std::move(native_states));
            if (!data) return {ApplyStatus::InvalidPatch, "Endstone rejected block data", current->revision};
            block->setData(*data, false);
            auto updated = capture(patch.location);
            return {ApplyStatus::Applied, "applied through public Endstone API", updated ? updated->revision : 0};
        } catch (const std::exception &e) {
            return {ApplyStatus::AdapterError, e.what(), current->revision};
        }
    }
private:
    endstone::Server &server_;
};
}
std::shared_ptr<IBlockAdapter> makeEndstonePublicAdapter(endstone::Server &server) {
    return std::make_shared<EndstonePublicAdapter>(server);
}
}
