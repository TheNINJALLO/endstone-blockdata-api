#include "endstone_blockdata/block_data_service.h"
#include "endstone_blockdata/container.h"
#include <algorithm>
#include <limits>
#include <stdexcept>

namespace endstone_blockdata {
namespace {
constexpr std::int64_t MaxCaptureRegionBlocks = 32768;
void mix(std::uint64_t &h, std::uint64_t v) { h ^= v + 0x9e3779b97f4a7c15ULL + (h << 6) + (h >> 2); }
std::uint64_t hashState(const BlockStateValue &v) {
    return std::visit([](const auto &x)->std::uint64_t { return std::hash<std::decay_t<decltype(x)>>{}(x); }, v);
}

const NbtCompound *asCompound(const NbtValue &value) {
    const auto *ptr = std::get_if<NbtValue::CompoundPtr>(&value.value);
    return ptr && *ptr ? ptr->get() : nullptr;
}

const NbtValue *findField(const NbtCompound &compound,
                          std::initializer_list<std::string_view> keys) {
    for (const auto key : keys) {
        const auto it = compound.find(std::string(key));
        if (it != compound.end()) return &it->second;
    }
    return nullptr;
}

std::optional<std::int64_t> integerField(const NbtCompound &compound,
                                         std::initializer_list<std::string_view> keys) {
    const auto *value = findField(compound, keys);
    if (!value) return std::nullopt;
    return std::visit([](const auto &entry) -> std::optional<std::int64_t> {
        using T = std::decay_t<decltype(entry)>;
        if constexpr (std::is_same_v<T, std::int8_t> || std::is_same_v<T, std::int16_t> ||
                      std::is_same_v<T, std::int32_t> || std::is_same_v<T, std::int64_t>) {
            return static_cast<std::int64_t>(entry);
        }
        return std::nullopt;
    }, value->value);
}

std::optional<std::int64_t> integerValue(const NbtValue &value) {
    return std::visit([](const auto &entry) -> std::optional<std::int64_t> {
        using T = std::decay_t<decltype(entry)>;
        if constexpr (std::is_same_v<T, std::int8_t> ||
                      std::is_same_v<T, std::int16_t> ||
                      std::is_same_v<T, std::int32_t> ||
                      std::is_same_v<T, std::int64_t>) {
            return static_cast<std::int64_t>(entry);
        }
        return std::nullopt;
    }, value.value);
}

std::optional<std::string> stringField(const NbtCompound &compound,
                                       std::initializer_list<std::string_view> keys) {
    const auto *value = findField(compound, keys);
    if (!value) return std::nullopt;
    if (const auto *text = std::get_if<std::string>(&value->value)) return *text;
    return std::nullopt;
}

bool isChiseledBookId(std::string_view id) {
    return id == "minecraft:book" || id == "minecraft:writable_book" ||
           id == "minecraft:written_book" || id == "minecraft:enchanted_book";
}
}
std::uint64_t calculateRevision(const BlockSnapshot &s) {
    std::uint64_t h = std::hash<std::string>{}(s.type);
    mix(h, s.runtime_id);
    mix(h, static_cast<std::uint64_t>(s.block_entity_status));
    std::vector<std::string> keys; keys.reserve(s.states.size());
    for (const auto &[k,_] : s.states) keys.push_back(k);
    std::sort(keys.begin(), keys.end());
    for (const auto &k : keys) { mix(h, std::hash<std::string>{}(k)); mix(h, hashState(s.states.at(k))); }
    if (s.block_entity) {
        mix(h, std::hash<std::string>{}(s.block_entity->type));
        mix(h, hashNbt(s.block_entity->nbt));
        mix(h, s.block_entity->is_container ? 1U : 0U);
        mix(h, static_cast<std::uint64_t>(
                   static_cast<std::int64_t>(s.block_entity->container_size)));
        std::vector<std::pair<std::int32_t, std::uint64_t>> inventory;
        inventory.reserve(s.block_entity->inventory.size());
        for (const auto &slot : s.block_entity->inventory)
            inventory.emplace_back(slot.slot, hashNbt(slot.item));
        std::sort(inventory.begin(), inventory.end());
        for (const auto &[slot, item_revision] : inventory) {
            mix(h, static_cast<std::uint64_t>(static_cast<std::int64_t>(slot)));
            mix(h, item_revision);
        }
    }
    return h;
}

BlockDataService::BlockDataService(std::shared_ptr<IBlockAdapter> adapter) : adapter_(std::move(adapter)) {
    if (!adapter_) throw std::invalid_argument("adapter must not be null");
}
std::optional<BlockSnapshot> BlockDataService::capture(const BlockLocation &l) { return adapter_->capture(l); }
std::vector<BlockSnapshot> BlockDataService::captureRegion(const BlockRegion &r) {
    if (r.minimum.dimension != r.maximum.dimension) throw std::invalid_argument("region dimensions differ");
    const auto min_x=std::min<std::int64_t>(r.minimum.x,r.maximum.x);
    const auto min_y=std::min<std::int64_t>(r.minimum.y,r.maximum.y);
    const auto min_z=std::min<std::int64_t>(r.minimum.z,r.maximum.z);
    const auto max_x=std::max<std::int64_t>(r.minimum.x,r.maximum.x);
    const auto max_y=std::max<std::int64_t>(r.minimum.y,r.maximum.y);
    const auto max_z=std::max<std::int64_t>(r.minimum.z,r.maximum.z);
    const auto width=max_x-min_x+1;
    const auto height=max_y-min_y+1;
    const auto depth=max_z-min_z+1;
    if(width>MaxCaptureRegionBlocks||height>MaxCaptureRegionBlocks||depth>MaxCaptureRegionBlocks||
       width*height>MaxCaptureRegionBlocks||width*height*depth>MaxCaptureRegionBlocks)
        throw std::length_error("capture region exceeds 32768 blocks");
    std::vector<BlockSnapshot> out;
    out.reserve(static_cast<std::size_t>(width*height*depth));
    for (std::int64_t x=min_x; x<=max_x; ++x)
      for (std::int64_t y=min_y; y<=max_y; ++y)
        for (std::int64_t z=min_z; z<=max_z; ++z) {
            auto s=capture({r.minimum.dimension,static_cast<int>(x),static_cast<int>(y),static_cast<int>(z)});
            if(s) out.push_back(std::move(*s));
        }
    return out;
}
ApplyResult BlockDataService::apply(const BlockPatch &p, ConflictPolicy policy) {
    if (policy != ConflictPolicy::FailIfChanged && policy != ConflictPolicy::Force) {
        return {ApplyStatus::Unsupported,
                "conflict policy is not implemented; use FailIfChanged or Force", 0};
    }
    if (p.location.dimension.empty())
        return {ApplyStatus::InvalidPatch, "block dimension must not be empty", 0};
    if (p.replacement_type && p.replacement_type->empty())
        return {ApplyStatus::InvalidPatch, "replacement block type must not be empty", 0};
    std::string validation_error;
    for (const auto &[key, value] : p.nbt_updates) {
        if (!validateNbtPayload(value, &validation_error))
            return {ApplyStatus::InvalidPatch,
                    "invalid NBT update '" + key + "': " + validation_error, 0};
    }
    for (const auto &[slot, item] : p.inventory_updates) {
        if (slot < 0)
            return {ApplyStatus::InvalidPatch, "inventory update slot must be non-negative", 0};
        if (!validateNbtPayload(item.item, &validation_error))
            return {ApplyStatus::InvalidPatch,
                    "invalid inventory item at slot " + std::to_string(slot) + ": " +
                        validation_error,
                    0};
    }
    if (std::ranges::any_of(p.inventory_removals, [](std::int32_t slot) { return slot < 0; }))
        return {ApplyStatus::InvalidPatch, "inventory removal slot must be non-negative", 0};
    return adapter_->apply(p, policy);
}
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
    const auto current = getSlot(slot);
    p.inventory_updates[slot]={slot,std::move(item),current ? current->revision : 0}; return p;
}
BlockPatch ContainerView::clearSlot(std::int32_t slot) const {
    BlockPatch p; p.location=snapshot_.location; p.expected_revision=snapshot_.revision; p.inventory_removals.insert(slot); return p;
}

ShelfView::ShelfView(BlockSnapshot snapshot) : snapshot_(std::move(snapshot)) {
    if (snapshot_.block_entity_status != BlockEntityCaptureStatus::Captured ||
        !snapshot_.block_entity || !snapshot_.block_entity->is_container) {
        throw std::invalid_argument("shelf capture is incomplete or unavailable");
    }
    const auto &entity = *snapshot_.block_entity;
    if (entity.type == "minecraft:shelf") kind_ = ShelfKind::Shelf;
    else if (entity.type == "minecraft:chiseled_bookshelf") kind_ = ShelfKind::ChiseledBookshelf;
    else throw std::invalid_argument("block actor is not a supported shelf");

    if (entity.container_size != capacity())
        throw std::invalid_argument("shelf container capacity does not match the exact actor contract");

    std::vector<bool> occupied(static_cast<std::size_t>(capacity()), false);
    for (const auto &item : entity.inventory) {
        validateSlot(item.slot);
        const auto index = static_cast<std::size_t>(item.slot);
        if (occupied[index])
            throw std::invalid_argument("shelf capture contains a duplicate slot");
        occupied[index] = true;
    }
}

std::int32_t ShelfView::capacity() const noexcept {
    return kind_ == ShelfKind::Shelf ? 3 : 6;
}

void ShelfView::validateSlot(std::int32_t slot) const {
    if (slot < 0 || slot >= capacity()) throw std::out_of_range("shelf slot is out of range");
}

void ShelfView::validateItem(const NbtValue &item) const {
    std::string error;
    if (!validateNbtPayload(item, &error))
        throw std::invalid_argument("invalid shelf item NBT: " + error);
    const auto *compound = asCompound(item);
    if (!compound) throw std::invalid_argument("shelf item must be an NBT compound");
    const auto id = stringField(*compound, {"Name", "name", "id"});
    if (!id || id->empty()) throw std::invalid_argument("shelf item has no item identifier");
    std::int64_t count = 1;
    if (const auto *count_value = findField(*compound, {"Count", "count"})) {
        const auto parsed = integerValue(*count_value);
        if (!parsed)
            throw std::invalid_argument("shelf item count must be an integer");
        count = *parsed;
    }
    if (count < 1 || count > std::numeric_limits<std::uint8_t>::max())
        throw std::invalid_argument("shelf item count is out of range");
    if (kind_ == ShelfKind::ChiseledBookshelf &&
        (count != 1 || !isChiseledBookId(*id))) {
        throw std::invalid_argument(
            "chiseled bookshelf slots accept exactly one supported book");
    }
}

std::vector<std::optional<InventorySlotSnapshot>> ShelfView::slots() const {
    std::vector<std::optional<InventorySlotSnapshot>> output(
        static_cast<std::size_t>(capacity()));
    for (const auto &item : snapshot_.block_entity->inventory)
        output[static_cast<std::size_t>(item.slot)] = item;
    return output;
}

std::optional<InventorySlotSnapshot> ShelfView::getSlot(std::int32_t slot) const {
    validateSlot(slot);
    for (const auto &item : snapshot_.block_entity->inventory)
        if (item.slot == slot) return item;
    return std::nullopt;
}

BlockPatch ShelfView::patchSlot(std::int32_t slot, NbtValue item) const {
    std::map<std::int32_t, NbtValue> updates;
    updates.emplace(slot, std::move(item));
    return patchSlots(std::move(updates));
}

BlockPatch ShelfView::clearSlot(std::int32_t slot) const {
    return patchSlots({}, {slot});
}

BlockPatch ShelfView::patchSlots(std::map<std::int32_t, NbtValue> updates,
                                 std::set<std::int32_t> removals) const {
    for (const auto &[slot, item] : updates) {
        validateSlot(slot);
        validateItem(item);
        if (removals.contains(slot))
            throw std::invalid_argument(
                "a shelf slot cannot be updated and removed in one patch");
    }
    for (const auto slot : removals) validateSlot(slot);

    BlockPatch patch;
    patch.location = snapshot_.location;
    patch.expected_revision = snapshot_.revision;
    patch.inventory_removals = std::move(removals);
    for (auto &[slot, item] : updates) {
        const auto current = getSlot(slot);
        patch.inventory_updates[slot] = {
            slot, std::move(item), current ? current->revision : 0};
    }
    return patch;
}

BlockPatch ShelfView::replaceSlots(
    std::vector<std::optional<NbtValue>> contents) const {
    if (contents.size() != static_cast<std::size_t>(capacity()))
        throw std::invalid_argument(
            "replacement shelf contents must match the exact capacity");
    std::map<std::int32_t, NbtValue> updates;
    std::set<std::int32_t> removals;
    for (std::int32_t slot = 0; slot < capacity(); ++slot) {
        auto &item = contents[static_cast<std::size_t>(slot)];
        if (item) updates.emplace(slot, std::move(*item));
        else removals.insert(slot);
    }
    return patchSlots(std::move(updates), std::move(removals));
}
}
