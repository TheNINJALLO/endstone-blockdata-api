#include "endstone_blockdata/bds_26_30_adapter.h"
#include "endstone_blockdata/endstone_adapter.h"

#include <endstone/endstone.hpp>
#include "bedrock/nbt/compound_tag.h"
#include "bedrock/world/container.h"
#include "bedrock/world/item/item_stack.h"
#include "bedrock/world/level/block/actor/block_actor.h"
#include "bedrock/world/level/block/actor/vanilla_block_actor.h"
#include "bedrock/world/level/block_source.h"
#include "endstone/core/level/dimension.h"

#include <algorithm>
#include <cstddef>
#include <exception>
#include <limits>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <type_traits>
#include <vector>

namespace endstone_blockdata {
namespace {
std::string blockActorTypeName(BlockActorType type) {
    switch (type) {
    case BlockActorType::Furnace: return "minecraft:furnace";
    case BlockActorType::Chest: return "minecraft:chest";
    case BlockActorType::Sign: return "minecraft:sign";
    case BlockActorType::MobSpawner: return "minecraft:mob_spawner";
    case BlockActorType::BrewingStand: return "minecraft:brewing_stand";
    case BlockActorType::Dispenser: return "minecraft:dispenser";
    case BlockActorType::Dropper: return "minecraft:dropper";
    case BlockActorType::Hopper: return "minecraft:hopper";
    case BlockActorType::Beacon: return "minecraft:beacon";
    case BlockActorType::EnderChest: return "minecraft:ender_chest";
    case BlockActorType::ShulkerBox: return "minecraft:shulker_box";
    case BlockActorType::CommandBlock: return "minecraft:command_block";
    case BlockActorType::StructureBlock: return "minecraft:structure_block";
    case BlockActorType::Lectern: return "minecraft:lectern";
    case BlockActorType::BlastFurnace: return "minecraft:blast_furnace";
    case BlockActorType::Smoker: return "minecraft:smoker";
    case BlockActorType::BarrelBlock: return "minecraft:barrel";
    case BlockActorType::Beehive: return "minecraft:beehive";
    case BlockActorType::HangingSign: return "minecraft:hanging_sign";
    case BlockActorType::Crafter: return "minecraft:crafter";
    case BlockActorType::TrialSpawner: return "minecraft:trial_spawner";
    case BlockActorType::Vault: return "minecraft:vault";
    default: return "minecraft:block_actor_" + std::to_string(static_cast<unsigned>(type));
    }
}

const NbtCompound *compoundOf(const NbtValue &value) {
    const auto *ptr = std::get_if<NbtValue::CompoundPtr>(&value.value);
    return ptr && *ptr ? ptr->get() : nullptr;
}

const NbtList *listOf(const NbtValue &value) {
    const auto *ptr = std::get_if<NbtValue::ListPtr>(&value.value);
    return ptr && *ptr ? ptr->get() : nullptr;
}

const NbtValue *field(const NbtCompound &compound, std::initializer_list<std::string_view> keys) {
    for (auto key : keys) {
        auto it = compound.find(std::string(key));
        if (it != compound.end()) return &it->second;
    }
    return nullptr;
}

std::optional<std::string> stringField(const NbtCompound &compound, std::initializer_list<std::string_view> keys) {
    if (const auto *v = field(compound, keys)) {
        if (const auto *value = std::get_if<std::string>(&v->value)) return *value;
    }
    return std::nullopt;
}

std::int32_t intValue(const NbtValue &value, std::int32_t fallback = 0) {
    return std::visit([fallback](const auto &v) -> std::int32_t {
        using T = std::decay_t<decltype(v)>;
        if constexpr (std::is_same_v<T, bool>) return v ? 1 : 0;
        else if constexpr (std::is_same_v<T, std::int8_t> || std::is_same_v<T, std::int16_t> ||
                           std::is_same_v<T, std::int32_t> || std::is_same_v<T, std::int64_t>) {
            if (v > std::numeric_limits<std::int32_t>::max() || v < std::numeric_limits<std::int32_t>::min()) return fallback;
            return static_cast<std::int32_t>(v);
        }
        return fallback;
    }, value.value);
}

std::int32_t intField(const NbtCompound &compound, std::initializer_list<std::string_view> keys,
                      std::int32_t fallback = 0) {
    if (const auto *v = field(compound, keys)) return intValue(*v, fallback);
    return fallback;
}

NbtValue fromNativeTag(const Tag &tag) {
    switch (tag.getId()) {
    case Tag::Type::End: return {};
    case Tag::Type::Byte: return static_cast<std::int8_t>(static_cast<const ByteTag &>(tag).data);
    case Tag::Type::Short: return static_cast<const ShortTag &>(tag).data;
    case Tag::Type::Int: return static_cast<const IntTag &>(tag).data;
    case Tag::Type::Int64: return static_cast<const Int64Tag &>(tag).data;
    case Tag::Type::Float: return static_cast<const FloatTag &>(tag).data;
    case Tag::Type::Double: return static_cast<const DoubleTag &>(tag).data;
    case Tag::Type::String: return static_cast<const StringTag &>(tag).data;
    case Tag::Type::ByteArray: {
        ByteArray out;
        for (auto v : static_cast<const ByteArrayTag &>(tag).data) out.push_back(static_cast<std::int8_t>(v));
        return out;
    }
    case Tag::Type::IntArray: return static_cast<const IntArrayTag &>(tag).data;
    case Tag::Type::List: {
        const auto &list = static_cast<const ListTag &>(tag);
        NbtList out;
        out.reserve(list.size());
        for (std::size_t i = 0; i < list.size(); ++i) {
            if (const auto *entry = list.get(static_cast<int>(i))) out.push_back(fromNativeTag(*entry));
        }
        return NbtValue::list(std::move(out));
    }
    case Tag::Type::Compound: {
        const auto &compound = static_cast<const CompoundTag &>(tag);
        NbtCompound out;
        for (const auto &[key, entry] : compound) {
            if (const auto *t = entry.get()) out.emplace(key, fromNativeTag(*t));
        }
        return NbtValue::compound(std::move(out));
    }
    default: return {};
    }
}

std::unique_ptr<Tag> toNativeTag(const NbtValue &value) {
    return std::visit([](const auto &v) -> std::unique_ptr<Tag> {
        using T = std::decay_t<decltype(v)>;
        if constexpr (std::is_same_v<T, std::monostate>) return std::make_unique<EndTag>();
        else if constexpr (std::is_same_v<T, bool>) return std::make_unique<ByteTag>(v ? 1 : 0);
        else if constexpr (std::is_same_v<T, std::int8_t>) return std::make_unique<ByteTag>(static_cast<std::uint8_t>(v));
        else if constexpr (std::is_same_v<T, std::int16_t>) return std::make_unique<ShortTag>(v);
        else if constexpr (std::is_same_v<T, std::int32_t>) return std::make_unique<IntTag>(v);
        else if constexpr (std::is_same_v<T, std::int64_t>) return std::make_unique<Int64Tag>(v);
        else if constexpr (std::is_same_v<T, float>) return std::make_unique<FloatTag>(v);
        else if constexpr (std::is_same_v<T, double>) return std::make_unique<DoubleTag>(v);
        else if constexpr (std::is_same_v<T, std::string>) return std::make_unique<StringTag>(v);
        else if constexpr (std::is_same_v<T, ByteArray>) {
            ByteArrayTag::ArrayData data;
            data.reserve(v.size());
            for (auto n : v) data.push_back(static_cast<char>(n));
            return std::make_unique<ByteArrayTag>(std::move(data));
        } else if constexpr (std::is_same_v<T, IntArray>) return std::make_unique<IntArrayTag>(v);
        else if constexpr (std::is_same_v<T, LongArray>) {
            auto list = std::make_unique<ListTag>();
            for (auto n : v) list->add(std::make_unique<Int64Tag>(n));
            return list;
        } else if constexpr (std::is_same_v<T, NbtValue::ListPtr>) {
            auto list = std::make_unique<ListTag>();
            if (v) for (const auto &entry : *v) list->add(toNativeTag(entry));
            return list;
        } else if constexpr (std::is_same_v<T, NbtValue::CompoundPtr>) {
            auto compound = std::make_unique<CompoundTag>();
            if (v) for (const auto &[key, entry] : *v) compound->put(key, toNativeTag(entry));
            return compound;
        }
    }, value.value);
}

std::unique_ptr<CompoundTag> toNativeCompound(const NbtValue &value) {
    auto tag = toNativeTag(value);
    if (!tag || tag->getId() != Tag::Type::Compound) return {};
    return std::unique_ptr<CompoundTag>(static_cast<CompoundTag *>(tag.release()));
}

CompoundTag makeItemTag(int slot, const ItemStack &item) {
    CompoundTag out;
    out.putByte("Slot", static_cast<std::uint8_t>(slot));
    out.putString("Name", item.getName());
    out.putByte("Count", item.getCount());
    out.putShort("Damage", item.getDamageValue());
    out.putShort("Aux", item.getAuxValue());
    out.putShort("LegacyId", item.getId());
    if (!item.getCustomName().empty()) out.putString("CustomName", item.getCustomName());
    if (const auto *user = item.getUserData()) out.putCompound("tag", user->clone());

    if (!item.getCanPlaceOn().empty()) {
        ListTag list;
        for (const auto &type : item.getCanPlaceOn()) {
            if (type) list.add(std::make_unique<StringTag>(type->getName().getString()));
        }
        out.put("CanPlaceOn", list.copy());
    }
    if (!item.getCanDestroy().empty()) {
        ListTag list;
        for (const auto &type : item.getCanDestroy()) {
            if (type) list.add(std::make_unique<StringTag>(type->getName().getString()));
        }
        out.put("CanDestroy", list.copy());
    }
    return out;
}

NbtValue itemSnapshot(int slot, const ItemStack &item) {
    if (item.isNull()) return NbtValue::compound({{"Slot", static_cast<std::int32_t>(slot)}, {"empty", true}});
    auto native = makeItemTag(slot, item);
    return fromNativeTag(native);
}

std::vector<std::string> stringListField(const NbtCompound &compound, std::initializer_list<std::string_view> keys) {
    std::vector<std::string> out;
    const auto *v = field(compound, keys);
    if (!v) return out;
    const auto *list = listOf(*v);
    if (!list) return out;
    for (const auto &entry : *list) if (const auto *s = std::get_if<std::string>(&entry.value)) out.push_back(*s);
    return out;
}

std::optional<ItemStack> itemFromNbt(const NbtValue &value) {
    const auto *item = compoundOf(value);
    if (!item) return std::nullopt;
    if (const auto *empty = field(*item, {"empty"}); empty && intValue(*empty, 0) != 0) return ItemStack::EMPTY_ITEM;

    auto name = stringField(*item, {"Name", "name"});
    if (!name || name->empty()) return std::nullopt;
    const int count = std::clamp(intField(*item, {"Count", "count"}, 1), 1, 255);
    const int aux = intField(*item, {"Damage", "Aux", "aux"}, 0);

    std::unique_ptr<CompoundTag> user_data;
    if (const auto *tag = field(*item, {"tag", "user_data"})) user_data = toNativeCompound(*tag);
    ItemStack stack(*name, count, aux, user_data.get());

    auto can_place = stringListField(*item, {"CanPlaceOn", "can_place_on"});
    if (!can_place.empty()) stack.setCanPlaceOn(can_place);
    auto can_destroy = stringListField(*item, {"CanDestroy", "can_destroy"});
    if (!can_destroy.empty()) stack.setCanDestroy(can_destroy);
    return stack;
}

struct ActorAccess {
    BlockSource *source{};
    BlockActor *actor{};
    IVanillaMainBlockActorComponent *main{};
    Container *container{};
};

std::optional<ActorAccess> locateActor(endstone::Server &server, const BlockLocation &location) {
    auto *level = server.getLevel();
    auto *dimension = level ? level->getDimension(location.dimension) : nullptr;
    auto *exact_dimension = dynamic_cast<endstone::core::EndstoneDimension *>(dimension);
    if (!exact_dimension) return std::nullopt;

    auto &source = exact_dimension->getHandle().getBlockSourceFromMainChunkSource();
    const ::BlockPos position(location.x, location.y, location.z);
    auto *actor = const_cast<BlockActor *>(source.getBlockEntity(position));
    if (!actor) return std::nullopt;

    auto *main = reinterpret_cast<IVanillaMainBlockActorComponent *>(
        reinterpret_cast<std::byte *>(actor) + sizeof(BlockActor));
    if (main->getBlockActorType() != actor->getType()) return std::nullopt;

    return ActorAccess{&source, actor, main, main->getContainer()};
}

CompoundTag captureCanonicalActorTag(const ActorAccess &access, const BlockLocation &location,
                                     std::string_view build) {
    CompoundTag root;
    root.putString("id", blockActorTypeName(access.actor->getType()));
    root.putInt("x", location.x);
    root.putInt("y", location.y);
    root.putInt("z", location.z);
    root.putInt("_endstone_actor_type", static_cast<std::int32_t>(access.actor->getType()));
    root.putString("_endstone_bds_build", std::string(build));
    root.putBoolean("_endstone_changed", access.main->isChanged());
    if (access.main->hasCustomName()) root.putString("CustomName", access.main->getName());

    if (access.container) {
        access.container->addAdditionalSaveData(root);
        root.putInt("_endstone_container_size", access.container->getContainerSize());
        ListTag items;
        for (int slot = 0; slot < access.container->getContainerSize(); ++slot) {
            const auto &item = access.container->getItem(slot);
            if (!item.isNull()) {
                auto item_tag = makeItemTag(slot, item);
                items.add(item_tag.copy());
            }
        }
        root.put("Items", items.copy());
    }
    return root;
}

bool applyItems(Container &container, const NbtValue &value, std::string &error) {
    const auto *items = listOf(value);
    if (!items) { error = "Items must be an NBT list"; return false; }

    // Parse and validate the entire replacement first. A malformed entry must
    // never empty or partially rewrite a live container.
    std::vector<std::pair<int, ItemStack>> replacements;
    replacements.reserve(items->size());
    std::vector<bool> occupied(static_cast<std::size_t>(container.getContainerSize()), false);
    for (const auto &entry : *items) {
        const auto *compound = compoundOf(entry);
        if (!compound) { error = "Items entries must be compounds"; return false; }
        const int slot = intField(*compound, {"Slot", "slot"}, -1);
        if (slot < 0 || slot >= container.getContainerSize()) { error = "Items slot out of range"; return false; }
        if (occupied[static_cast<std::size_t>(slot)]) { error = "Items contains a duplicate slot"; return false; }
        auto stack = itemFromNbt(entry);
        if (!stack) { error = "invalid item NBT"; return false; }
        occupied[static_cast<std::size_t>(slot)] = true;
        replacements.emplace_back(slot, std::move(*stack));
    }

    container.removeAllItems();
    for (auto &[slot, stack] : replacements) {
        container.setItem(slot, stack);
        container.setContainerChanged(slot);
    }
    return true;
}

class Bds2630BlockAdapter final : public IBedrockBlockAdapter {
public:
    explicit Bds2630BlockAdapter(endstone::Server &server)
        : server_(server), public_(makeEndstonePublicAdapter(server)) {}

    std::string_view name() const noexcept override { return "bds-26.30-exact-nbt"; }
    AdapterCapabilities capabilities() const noexcept override {
        AdapterCapabilities out;
        out.block_states = true;
        out.block_writes = true;
        out.block_entity_nbt = true;
        out.block_entity_nbt_write = true;
        out.canonical_actor_nbt = true;
        out.item_user_nbt = true;
        out.inventory = true;
        out.mark_dirty = true;
        out.client_updates = true;
        out.block_entity_metadata = true;
        out.container_save_nbt = true;
        // This adapter intentionally labels its output as canonical live NBT. A byte-identical
        // hidden BlockActor::save/load call is not claimed without binary signature validation.
        out.raw_block_entity_nbt = false;
        return out;
    }

    bool verifySymbols() noexcept override {
        try {
            return isSupportedBds2630Build(server_.getMinecraftVersion()) &&
                   sizeof(void *) == 8;
        } catch (...) {
            return false;
        }
    }

    std::string bedrockBuild() const override { return server_.getMinecraftVersion(); }

    std::optional<BlockSnapshot> capture(const BlockLocation &location) override {
        if (!server_.isPrimaryThread() || !isSupportedBds2630Build(server_.getMinecraftVersion())) return std::nullopt;
        auto snapshot = public_->capture(location);
        if (!snapshot) return std::nullopt;

        auto access = locateActor(server_, location);
        if (!access) return snapshot;

        auto native = captureCanonicalActorTag(*access, location, server_.getMinecraftVersion());
        BlockEntitySnapshot entity;
        entity.type = blockActorTypeName(access->actor->getType());
        entity.nbt = fromNativeTag(native);
        entity.raw_snbt = native.toString();
        entity.canonical_nbt = true;

        if (access->container) {
            entity.inventory.reserve(access->container->getContainerSize());
            for (int slot = 0; slot < access->container->getContainerSize(); ++slot) {
                InventorySlotSnapshot item;
                item.slot = slot;
                item.item = itemSnapshot(slot, access->container->getItem(slot));
                item.revision = hashNbt(item.item);
                entity.inventory.push_back(std::move(item));
            }
        }

        snapshot->block_entity = std::move(entity);
        snapshot->revision = calculateRevision(*snapshot);
        return snapshot;
    }

    ApplyResult apply(const BlockPatch &patch, ConflictPolicy policy) override {
        if (!server_.isPrimaryThread()) return {ApplyStatus::AdapterError, "live apply must run on primary thread", 0};
        if (!isSupportedBds2630Build(server_.getMinecraftVersion()))
            return {ApplyStatus::Unsupported, "adapter refuses non-26.30-family BDS build", 0};

        auto current = capture(patch.location);
        if (!current) return {ApplyStatus::ChunkUnavailable, "block or chunk unavailable", 0};
        if (patch.expected_revision && policy != ConflictPolicy::Force && *patch.expected_revision != current->revision)
            return {ApplyStatus::Conflict, "revision changed", current->revision};

        if (patch.replacement_type || !patch.state_updates.empty() || !patch.state_removals.empty()) {
            BlockPatch public_patch = patch;
            public_patch.expected_revision.reset();
            public_patch.nbt_updates.clear();
            public_patch.nbt_removals.clear();
            public_patch.inventory_updates.clear();
            public_patch.inventory_removals.clear();
            auto result = public_->apply(public_patch, ConflictPolicy::Force);
            if (!result.ok()) return result;
        }

        if (patch.nbt_updates.empty() && patch.nbt_removals.empty() &&
            patch.inventory_updates.empty() && patch.inventory_removals.empty()) {
            auto updated = capture(patch.location);
            return {ApplyStatus::Applied, "block data applied", updated ? updated->revision : 0};
        }

        auto access = locateActor(server_, patch.location);
        if (!access) return {ApplyStatus::Unsupported, "block has no supported vanilla block actor", current->revision};

        CompoundTag additional;
        bool has_additional = false;
        for (const auto &[key, value] : patch.nbt_updates) {
            if (key == "CustomName" || key == "custom_name") {
                if (!access->container) return {ApplyStatus::Unsupported, "CustomName currently requires a container block actor", current->revision};
                const auto *name = std::get_if<std::string>(&value.value);
                if (!name) return {ApplyStatus::InvalidPatch, "CustomName must be a string", current->revision};
                access->container->setCustomName(*name);
            } else if (key == "Items" || key == "items") {
                if (!access->container) return {ApplyStatus::Unsupported, "Items requires a container block actor", current->revision};
                std::string error;
                if (!applyItems(*access->container, value, error)) return {ApplyStatus::InvalidPatch, error, current->revision};
            } else if (key == "id" || key == "x" || key == "y" || key == "z" || key.starts_with("_endstone_")) {
                return {ApplyStatus::InvalidPatch, "identity and adapter metadata NBT fields are read-only", current->revision};
            } else {
                if (!access->container)
                    return {ApplyStatus::Unsupported, "generic non-container actor NBT write requires a native save/load hook", current->revision};
                additional.put(key, toNativeTag(value));
                has_additional = true;
            }
        }
        for (const auto &key : patch.nbt_removals) {
            if (key == "CustomName" || key == "custom_name") {
                if (!access->container) return {ApplyStatus::Unsupported, "CustomName currently requires a container block actor", current->revision};
                access->container->setCustomName("");
            } else if (key == "Items" || key == "items") {
                if (!access->container) return {ApplyStatus::Unsupported, "Items requires a container block actor", current->revision};
                access->container->removeAllItems();
            } else {
                return {ApplyStatus::Unsupported, "removing arbitrary additional-save keys is not supported by Container::readAdditionalSaveData", current->revision};
            }
        }
        if (has_additional) access->container->readAdditionalSaveData(additional);

        if ((!patch.inventory_updates.empty() || !patch.inventory_removals.empty()) && !access->container)
            return {ApplyStatus::Unsupported, "block actor is not a container", current->revision};

        for (const auto &[slot, item_patch] : patch.inventory_updates) {
            if (slot < 0 || slot >= access->container->getContainerSize())
                return {ApplyStatus::InvalidPatch, "inventory slot out of range", current->revision};
            auto stack = itemFromNbt(item_patch.item);
            if (!stack) return {ApplyStatus::InvalidPatch, "invalid canonical item NBT", current->revision};
            access->container->setItem(slot, *stack);
            access->container->setContainerChanged(slot);
        }
        for (int slot : patch.inventory_removals) {
            if (slot < 0 || slot >= access->container->getContainerSize())
                return {ApplyStatus::InvalidPatch, "inventory slot out of range", current->revision};
            access->container->setItem(slot, ItemStack::EMPTY_ITEM);
            access->container->setContainerChanged(slot);
        }

        // Validate the complete resulting projection before announcing the mutation.
        auto resulting_tag = captureCanonicalActorTag(*access, patch.location, server_.getMinecraftVersion());
        if (!access->main->validateData(resulting_tag))
            return {ApplyStatus::AdapterError, "block actor rejected the resulting canonical NBT", current->revision};

        access->main->setChanged();
        access->main->onChanged(*access->source);
        access->source->fireBlockEntityChanged(*access->actor);

        auto updated = capture(patch.location);
        return {ApplyStatus::Applied, "applied canonical block-actor NBT through exact BDS 26.30 adapter",
                updated ? updated->revision : 0};
    }

    bool markBlockActorDirty(const BlockLocation &location) override {
        auto access = locateActor(server_, location);
        if (!access) return false;
        access->main->setChanged();
        access->main->onChanged(*access->source);
        return true;
    }

    bool sendBlockActorUpdate(const BlockLocation &location) override {
        auto access = locateActor(server_, location);
        if (!access) return false;
        access->source->fireBlockEntityChanged(*access->actor);
        return true;
    }

private:
    endstone::Server &server_;
    std::shared_ptr<IBlockAdapter> public_;
};
}

std::shared_ptr<IBedrockBlockAdapter> makeBds2630Adapter(endstone::Server &server) {
    auto adapter = std::make_shared<Bds2630BlockAdapter>(server);
    return adapter->verifySymbols() ? adapter : nullptr;
}
}
