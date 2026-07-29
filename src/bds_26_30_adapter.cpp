#include "endstone_blockdata/bds_26_30_adapter.h"
#include "endstone_blockdata/endstone_adapter.h"
#include "native_item_bridge.h"

#include <endstone/endstone.hpp>
#include "bedrock/nbt/compound_tag.h"
#include "bedrock/world/container.h"
#include "bedrock/world/item/item.h"
#include "bedrock/world/item/item_stack.h"
#include "bedrock/world/level/block/actor/block_actor.h"
#include "bedrock/world/level/block/actor/vanilla_block_actor.h"
#include "bedrock/world/level/block_source.h"
#include "endstone/core/level/dimension.h"

#include <algorithm>
#include <cstddef>
#include <exception>
#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <string>
#include <string_view>
#include <type_traits>
#include <vector>

namespace endstone_blockdata {
namespace {
bool isExactRuntimeBuild(const endstone::Server &server) {
    return isExpectedBds2630Build(server.getMinecraftVersion(), ENDSTONE_BLOCKDATA_BDS_BUILD) &&
           isExpectedEndstoneVersion(server.getVersion(), ENDSTONE_BLOCKDATA_ENDSTONE_VERSION);
}

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
    case BlockActorType::ChiseledBookshelf: return "minecraft:chiseled_bookshelf";
    case BlockActorType::Crafter: return "minecraft:crafter";
    case BlockActorType::TrialSpawner: return "minecraft:trial_spawner";
    case BlockActorType::Vault: return "minecraft:vault";
    case BlockActorType::Shelf: return "minecraft:shelf";
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

std::optional<std::int64_t> integerValue(const NbtValue &value) {
    return std::visit([](const auto &v) -> std::optional<std::int64_t> {
        using T = std::decay_t<decltype(v)>;
        if constexpr (std::is_same_v<T, std::int8_t> || std::is_same_v<T, std::int16_t> ||
                      std::is_same_v<T, std::int32_t> || std::is_same_v<T, std::int64_t>) {
            return static_cast<std::int64_t>(v);
        }
        return std::nullopt;
    }, value.value);
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
    // Bundle/storage-item contents live in Bedrock's dynamic container, not in
    // ItemStackBase::mUserData. Flatten a copy so reads expose the serialized
    // contents without consuming or changing the live stack.
    ItemStack serialized(item);
    flattenNativeStorageItem(serialized);

    CompoundTag out;
    out.putByte("Slot", static_cast<std::uint8_t>(slot));
    // ItemStackBase::getName() is the translated/display name. Canonical item
    // NBT needs the registry identifier so a captured stack can be reapplied.
    const auto *definition = serialized.getItem();
    out.putString("Name", definition ? definition->getFullItemName() : serialized.getName());
    out.putByte("Count", serialized.getCount());
    out.putShort("Damage", serialized.getDamageValue());
    out.putShort("Aux", serialized.getAuxValue());
    out.putShort("LegacyId", serialized.getId());
    if (!serialized.getCustomName().empty()) out.putString("CustomName", serialized.getCustomName());
    if (const auto *user = serialized.getUserData()) out.putCompound("tag", user->clone());

    if (!serialized.getCanPlaceOn().empty()) {
        ListTag list;
        for (const auto &type : serialized.getCanPlaceOn()) {
            if (type) list.add(std::make_unique<StringTag>(type->getName().getString()));
        }
        out.put("CanPlaceOn", list.copy());
    }
    if (!serialized.getCanDestroy().empty()) {
        ListTag list;
        for (const auto &type : serialized.getCanDestroy()) {
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

bool isVanillaBundleIdentifier(std::string_view identifier) {
    constexpr std::string_view prefix = "minecraft:";
    if (!identifier.starts_with(prefix)) return false;
    const auto name = identifier.substr(prefix.size());
    return name == "bundle" || name.ends_with("_bundle");
}

bool hasSerializedStorageContents(const NbtCompound &item) {
    const auto *tag_value = field(item, {"tag", "user_data"});
    if (!tag_value) return false;
    const auto *tag = compoundOf(*tag_value);
    if (!tag) return false;
    const auto *contents = field(*tag, {"storage_item_component_content"});
    return contents && listOf(*contents);
}

std::optional<ItemStack> itemFromNbt(const NbtValue &value) {
    const auto *item = compoundOf(value);
    if (!item) return std::nullopt;
    if (const auto *empty = field(*item, {"empty"}); empty && intValue(*empty, 0) != 0) return ItemStack::EMPTY_ITEM;

    // The portable/Python API calls this field `id`; canonical Bedrock NBT
    // calls it `Name`. Accept both at the native boundary.
    auto name = stringField(*item, {"Name", "name", "id"});
    if (!name || name->empty()) return std::nullopt;
    // A bundle identifier without a serialized contents list is an incomplete
    // live snapshot, not an empty bundle. Refuse it at the native boundary so
    // direct raw patches cannot erase contents that the caller never saw.
    if (isVanillaBundleIdentifier(*name) &&
        !hasSerializedStorageContents(*item)) {
        return std::nullopt;
    }
    int count = 1;
    if (const auto *count_value = field(*item, {"Count", "count"})) {
        const auto parsed = integerValue(*count_value);
        if (!parsed || *parsed < 1 || *parsed > std::numeric_limits<std::uint8_t>::max())
            return std::nullopt;
        count = static_cast<int>(*parsed);
    }
    int aux = 0;
    if (const auto *aux_value = field(*item, {"Damage", "Aux", "aux"})) {
        const auto parsed = integerValue(*aux_value);
        if (!parsed || *parsed < std::numeric_limits<std::int16_t>::min() ||
            *parsed > std::numeric_limits<std::int16_t>::max()) return std::nullopt;
        aux = static_cast<int>(*parsed);
    }

    std::unique_ptr<CompoundTag> user_data;
    if (const auto *tag = field(*item, {"tag", "user_data"})) {
        user_data = toNativeCompound(*tag);
        if (!user_data) return std::nullopt;
    }
    ItemStack stack(*name, count, aux, user_data.get());
    // The Bedrock constructor returns a null stack when the identifier is not
    // registered or is incompatible with this world. Treat that as invalid
    // input; otherwise an "add" patch can silently clear the target slot.
    if (stack.isNull() || count > stack.getMaxStackSize()) return std::nullopt;

    auto can_place = stringListField(*item, {"CanPlaceOn", "can_place_on"});
    if (!can_place.empty() && !stack.setCanPlaceOn(can_place)) return std::nullopt;
    auto can_destroy = stringListField(*item, {"CanDestroy", "can_destroy"});
    if (!can_destroy.empty() && !stack.setCanDestroy(can_destroy)) return std::nullopt;
    return stack;
}

struct ActorAccess {
    Level *level{};
    BlockSource *source{};
    BlockActor *actor{};
    IVanillaMainBlockActorComponent *main{};
    Container *container{};
    int container_size{};
};

struct ActorLookup {
    std::optional<ActorAccess> access;
    BlockEntityCaptureStatus status{BlockEntityCaptureStatus::NoActor};
};

bool isSupportedVanillaActorType(BlockActorType type) {
    // Endstone v0.11.6 declares the vanilla actor component as the second
    // base of VanillaBlockActor. Data-driven and sentinel actor values do not
    // carry that exact ABI contract and must never be reinterpreted as one.
    switch (type) {
    case BlockActorType::Furnace:
    case BlockActorType::Chest:
    case BlockActorType::NetherReactor:
    case BlockActorType::Sign:
    case BlockActorType::MobSpawner:
    case BlockActorType::Skull:
    case BlockActorType::FlowerPot:
    case BlockActorType::BrewingStand:
    case BlockActorType::EnchantingTable:
    case BlockActorType::DaylightDetector:
    case BlockActorType::Music:
    case BlockActorType::Comparator:
    case BlockActorType::Dispenser:
    case BlockActorType::Dropper:
    case BlockActorType::Hopper:
    case BlockActorType::Cauldron:
    case BlockActorType::ItemFrame:
    case BlockActorType::PistonArm:
    case BlockActorType::MovingBlock:
    case BlockActorType::Chalkboard:
    case BlockActorType::Beacon:
    case BlockActorType::EndPortal:
    case BlockActorType::EnderChest:
    case BlockActorType::EndGateway:
    case BlockActorType::ShulkerBox:
    case BlockActorType::CommandBlock:
    case BlockActorType::Bed:
    case BlockActorType::Banner:
    case BlockActorType::StructureBlock:
    case BlockActorType::Jukebox:
    case BlockActorType::ChemistryTable:
    case BlockActorType::Conduit:
    case BlockActorType::JigsawBlock:
    case BlockActorType::Lectern:
    case BlockActorType::BlastFurnace:
    case BlockActorType::Smoker:
    case BlockActorType::Bell:
    case BlockActorType::Campfire:
    case BlockActorType::BarrelBlock:
    case BlockActorType::Beehive:
    case BlockActorType::Lodestone:
    case BlockActorType::SculkSensor:
    case BlockActorType::SporeBlossom:
    case BlockActorType::GlowItemFrame:
    case BlockActorType::SculkCatalyst:
    case BlockActorType::SculkShrieker:
    case BlockActorType::HangingSign:
    case BlockActorType::ChiseledBookshelf:
    case BlockActorType::BrushableBlock:
    case BlockActorType::DecoratedPot:
    case BlockActorType::CalibratedSculkSensor:
    case BlockActorType::Crafter:
    case BlockActorType::TrialSpawner:
    case BlockActorType::Vault:
    case BlockActorType::CreakingHeart:
    case BlockActorType::Shelf:
    case BlockActorType::CopperGolemStatue:
    case BlockActorType::PotentSulfurBlock:
        return true;
    case BlockActorType::Undefined:
    case BlockActorType::DataDriven:
    case BlockActorType::_count:
        return false;
    }
    return false;
}

bool isKnownContainerActorType(BlockActorType type) {
    switch (type) {
    case BlockActorType::Furnace:
    case BlockActorType::Chest:
    case BlockActorType::BrewingStand:
    case BlockActorType::Music:
    case BlockActorType::Dispenser:
    case BlockActorType::Dropper:
    case BlockActorType::Hopper:
    case BlockActorType::Beacon:
    case BlockActorType::EnderChest:
    case BlockActorType::ShulkerBox:
    case BlockActorType::Jukebox:
    case BlockActorType::ChemistryTable:
    case BlockActorType::Lectern:
    case BlockActorType::BlastFurnace:
    case BlockActorType::Smoker:
    case BlockActorType::Campfire:
    case BlockActorType::BarrelBlock:
    case BlockActorType::ChiseledBookshelf:
    case BlockActorType::DecoratedPot:
    case BlockActorType::Crafter:
    case BlockActorType::Shelf:
        return true;
    default:
        return false;
    }
}

std::optional<int> exactContainerSize(BlockActorType type) {
    switch (type) {
    case BlockActorType::Shelf: return 3;
    case BlockActorType::ChiseledBookshelf: return 6;
    default: return std::nullopt;
    }
}

bool isShelfActorType(BlockActorType type) {
    return type == BlockActorType::Shelf || type == BlockActorType::ChiseledBookshelf;
}

bool isChiseledBookshelfItem(const ItemStack &stack) {
    if (stack.isNull()) return true;
    const auto *definition = stack.getItem();
    if (!definition) return false;
    const auto name = definition->getFullItemName();
    return name == "minecraft:book" || name == "minecraft:writable_book" ||
           name == "minecraft:written_book" || name == "minecraft:enchanted_book";
}

bool validateContainerItem(const Container &container, BlockActorType actor_type,
                           const ItemStack &stack, std::string &error) {
    if (stack.isNull()) return true;
    const int container_max = container.getMaxStackSize();
    if (container_max < 1 || stack.getCount() > container_max) {
        error = "item count exceeds the live container stack limit";
        return false;
    }
    if (actor_type == BlockActorType::ChiseledBookshelf) {
        if (stack.getCount() != 1) {
            error = "chiseled bookshelf slots accept exactly one book";
            return false;
        }
        if (!isChiseledBookshelfItem(stack)) {
            error = "chiseled bookshelf slots accept only book, writable_book, written_book, or enchanted_book";
            return false;
        }
    }
    return true;
}

ActorLookup locateActor(endstone::Server &server, const BlockLocation &location) {
    auto *level = server.getLevel();
    auto *dimension = level ? level->getDimension(location.dimension) : nullptr;
    auto *exact_dimension = static_cast<endstone::core::EndstoneDimension *>(dimension);
    if (!exact_dimension) return {{}, BlockEntityCaptureStatus::DimensionUnavailable};

    auto &native_dimension = exact_dimension->getHandle();
    auto &native_level = native_dimension.getLevel();
    auto &source = native_dimension.getBlockSourceFromMainChunkSource();
    const ::BlockPos position(location.x, location.y, location.z);
    auto *actor = const_cast<BlockActor *>(source.getBlockEntity(position));
    if (!actor) return {};
    if (!isSupportedVanillaActorType(actor->getType())) {
        return {{}, BlockEntityCaptureStatus::UnsupportedActor};
    }

    // Use the compiler's exact multiple-inheritance adjustment from the
    // pinned Endstone declaration instead of hand-adding sizeof(BlockActor).
    // The actor-type allowlist above prevents invoking this interface for an
    // ABI family that is not declared as VanillaBlockActor.
    auto *vanilla = static_cast<VanillaBlockActor *>(actor);
    auto *main = static_cast<IVanillaMainBlockActorComponent *>(vanilla);
    if (main->getBlockActorType() != actor->getType()) {
        return {{}, BlockEntityCaptureStatus::ComponentMismatch};
    }

    auto *container = main->getContainer();
    if (!container) {
        const auto status = isKnownContainerActorType(actor->getType())
                                ? BlockEntityCaptureStatus::ContainerUnavailable
                                : BlockEntityCaptureStatus::Captured;
        return {ActorAccess{&native_level, &source, actor, main, nullptr, 0}, status};
    }

    constexpr int MaxSupportedContainerSlots = 4096;
    const int container_size = container->getContainerSize();
    if (container_size < 0 || container_size > MaxSupportedContainerSlots) {
        return {ActorAccess{&native_level, &source, actor, main, nullptr, 0},
                BlockEntityCaptureStatus::ContainerUnavailable};
    }
    if (const auto expected = exactContainerSize(actor->getType());
        expected && container_size != *expected) {
        return {ActorAccess{&native_level, &source, actor, main, nullptr, 0},
                BlockEntityCaptureStatus::ContainerUnavailable};
    }
    return {ActorAccess{&native_level, &source, actor, main, container, container_size},
            BlockEntityCaptureStatus::Captured};
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
    if (access.main->hasCustomName()) root.putString("CustomName", access.main->getName());

    if (access.container) {
        access.container->addAdditionalSaveData(root);
        root.putInt("_endstone_container_size", access.container_size);
        ListTag items;
        for (int slot = 0; slot < access.container_size; ++slot) {
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

using ItemReplacements = std::vector<std::pair<int, ItemStack>>;

bool parseItems(Container &container, BlockActorType actor_type, const NbtValue &value,
                ItemReplacements &replacements, std::string &error) {
    const auto *items = listOf(value);
    if (!items) { error = "Items must be an NBT list"; return false; }

    replacements.clear();
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
        if (!validateContainerItem(container, actor_type, *stack, error)) return false;
        occupied[static_cast<std::size_t>(slot)] = true;
        replacements.emplace_back(slot, std::move(*stack));
    }
    return true;
}

using ItemProjection = std::map<int, ItemStack>;

bool itemSlotMatches(const Container &container, int slot, const ItemStack *expected) {
    const auto &actual = container.getItem(slot);
    const bool expected_empty = !expected || expected->isNull();
    if (expected_empty || actual.isNull()) return expected_empty && actual.isNull();
    return nbtEqual(itemSnapshot(slot, *expected), itemSnapshot(slot, actual));
}

bool containerMatches(const Container &container, int container_size,
                      const ItemProjection &expected) {
    for (int slot = 0; slot < container_size; ++slot) {
        const auto it = expected.find(slot);
        const ItemStack *stack = it == expected.end() ? nullptr : &it->second;
        if (!itemSlotMatches(container, slot, stack)) return false;
    }
    return true;
}

void signalContainerChanged(ActorAccess &access, const std::set<int> &slots) {
    for (int slot : slots) access.container->setContainerChanged(slot);
    access.main->setChanged();
    access.main->onChanged(*access.source);
    access.source->fireBlockEntityChanged(*access.actor);
}

struct NativeMutationPlan {
    std::optional<std::string> custom_name;
    std::optional<ItemReplacements> replacement_items;
    std::vector<std::pair<std::string, NbtValue>> additional_updates;
    ItemReplacements inventory_updates;
    std::vector<int> inventory_removals;
};

bool isIdentityField(std::string_view key) {
    return key == "id" || key == "x" || key == "y" || key == "z" || key.starts_with("_endstone_");
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
            return isExactRuntimeBuild(server_) && sizeof(void *) == 8 &&
                   verifyNativeStorageItemBridge();
        } catch (...) {
            return false;
        }
    }

    std::string bedrockBuild() const override { return server_.getMinecraftVersion(); }

    std::optional<BlockSnapshot> capture(const BlockLocation &location) override {
        if (!server_.isPrimaryThread() || !isExactRuntimeBuild(server_)) return std::nullopt;
        auto snapshot = public_->capture(location);
        if (!snapshot) return std::nullopt;

        auto lookup = locateActor(server_, location);
        snapshot->block_entity_status = lookup.status;
        auto access = std::move(lookup.access);
        if (!access) {
            snapshot->revision = calculateRevision(*snapshot);
            return snapshot;
        }

        NativeItemRegistryScope item_registry_scope(*access->level);
        auto native = captureCanonicalActorTag(*access, location, server_.getMinecraftVersion());
        BlockEntitySnapshot entity;
        entity.type = blockActorTypeName(access->actor->getType());
        entity.nbt = fromNativeTag(native);
        entity.raw_snbt = native.toString();
        entity.canonical_nbt = true;
        entity.is_container = access->container != nullptr;

        if (access->container) {
            entity.container_size = access->container_size;
            entity.inventory.reserve(static_cast<std::size_t>(entity.container_size));
            for (int slot = 0; slot < entity.container_size; ++slot) {
                const auto &stack = access->container->getItem(slot);
                if (stack.isNull()) continue;
                InventorySlotSnapshot item;
                item.slot = slot;
                item.item = itemSnapshot(slot, stack);
                item.revision = hashNbt(item.item);
                entity.inventory.push_back(std::move(item));
            }
        }

        snapshot->block_entity = std::move(entity);
        snapshot->revision = calculateRevision(*snapshot);
        return snapshot;
    }

    ApplyResult apply(const BlockPatch &patch, ConflictPolicy policy) override {
        if (policy != ConflictPolicy::FailIfChanged && policy != ConflictPolicy::Force)
            return {ApplyStatus::Unsupported, "conflict policy is not implemented; use FailIfChanged or Force", 0};
        if (!server_.isPrimaryThread()) return {ApplyStatus::AdapterError, "live apply must run on primary thread", 0};
        if (!isExactRuntimeBuild(server_))
            return {ApplyStatus::Unsupported,
                    "adapter refuses a runtime other than BDS " ENDSTONE_BLOCKDATA_BDS_BUILD
                    " with Endstone " ENDSTONE_BLOCKDATA_ENDSTONE_VERSION, 0};

        auto current = capture(patch.location);
        if (!current) return {ApplyStatus::ChunkUnavailable, "block or chunk unavailable", 0};
        if (patch.expected_revision && policy != ConflictPolicy::Force && *patch.expected_revision != current->revision)
            return {ApplyStatus::Conflict, "revision changed", current->revision};

        const bool has_public_changes = patch.replacement_type || !patch.state_updates.empty() ||
                                        !patch.state_removals.empty();
        const bool has_native_changes = !patch.nbt_updates.empty() || !patch.nbt_removals.empty() ||
                                        !patch.inventory_updates.empty() || !patch.inventory_removals.empty();
        if (has_public_changes && has_native_changes) {
            return {ApplyStatus::Unsupported,
                    "mixed block-state and block-entity patches are not atomic; apply them separately",
                    current->revision};
        }

        if (has_public_changes) {
            BlockPatch public_patch = patch;
            public_patch.expected_revision.reset();
            auto result = public_->apply(public_patch, ConflictPolicy::Force);
            if (result.ok()) {
                // The public adapter cannot include exact actor/container
                // completeness in its fingerprint. Return the revision that a
                // subsequent capture through this exact service will observe.
                auto updated = capture(patch.location);
                result.resulting_revision = updated ? updated->revision : 0;
            }
            return result;
        }

        if (!has_native_changes)
            return {ApplyStatus::Applied, "block data unchanged", current->revision};

        auto lookup = locateActor(server_, patch.location);
        auto access = std::move(lookup.access);
        if (!access)
            return {ApplyStatus::Unsupported,
                    "block actor capture is unavailable: " +
                        std::string(blockEntityCaptureStatusName(lookup.status)),
                    current->revision};
        if (!access->container)
            return {ApplyStatus::Unsupported,
                    "container access is unavailable: " +
                        std::string(blockEntityCaptureStatusName(lookup.status)),
                    current->revision};

        NativeItemRegistryScope item_registry_scope(*access->level);
        const auto actor_type = access->actor->getType();

        // Shelves have actor-specific display, comparator and powered-swap
        // state. Until the exact actor save/load ABI is exposed, accept only
        // their live inventory surface; routing arbitrary keys through
        // Container::readAdditionalSaveData can silently ignore them.
        if (isShelfActorType(actor_type)) {
            for (const auto &[key, _] : patch.nbt_updates) {
                if (key != "Items" && key != "items") {
                    return {ApplyStatus::Unsupported,
                            "shelf actors currently accept inventory changes only",
                            current->revision};
                }
            }
            for (const auto &key : patch.nbt_removals) {
                if (key != "Items" && key != "items") {
                    return {ApplyStatus::Unsupported,
                            "shelf actors currently accept inventory changes only",
                            current->revision};
                }
            }
        }

        NativeMutationPlan plan;
        bool custom_name_seen = false;
        bool items_seen = false;
        for (const auto &[key, value] : patch.nbt_updates) {
            std::string validation_error;
            if (!validateNbtPayload(value, &validation_error)) {
                return {ApplyStatus::InvalidPatch,
                        "invalid NBT update '" + key + "': " + validation_error,
                        current->revision};
            }
            if (key == "CustomName" || key == "custom_name") {
                if (custom_name_seen)
                    return {ApplyStatus::InvalidPatch, "CustomName was specified more than once", current->revision};
                const auto *name = std::get_if<std::string>(&value.value);
                if (!name) return {ApplyStatus::InvalidPatch, "CustomName must be a string", current->revision};
                plan.custom_name = *name;
                custom_name_seen = true;
            } else if (key == "Items" || key == "items") {
                if (items_seen)
                    return {ApplyStatus::InvalidPatch, "Items was specified more than once", current->revision};
                plan.replacement_items.emplace();
                std::string error;
                if (!parseItems(*access->container, actor_type, value,
                                *plan.replacement_items, error))
                    return {ApplyStatus::InvalidPatch, error, current->revision};
                items_seen = true;
            } else if (isIdentityField(key)) {
                return {ApplyStatus::InvalidPatch, "identity and adapter metadata NBT fields are read-only", current->revision};
            } else {
                if (patch.nbt_removals.contains(key))
                    return {ApplyStatus::InvalidPatch, "an NBT field cannot be updated and removed in one patch", current->revision};
                plan.additional_updates.emplace_back(key, value);
            }
        }
        for (const auto &key : patch.nbt_removals) {
            if (key == "CustomName" || key == "custom_name") {
                if (custom_name_seen)
                    return {ApplyStatus::InvalidPatch, "CustomName cannot be updated and removed in one patch", current->revision};
                plan.custom_name = std::string{};
                custom_name_seen = true;
            } else if (key == "Items" || key == "items") {
                if (items_seen)
                    return {ApplyStatus::InvalidPatch, "Items cannot be updated and removed in one patch", current->revision};
                plan.replacement_items.emplace();
                items_seen = true;
            } else if (isIdentityField(key)) {
                return {ApplyStatus::InvalidPatch, "identity and adapter metadata NBT fields are read-only", current->revision};
            } else {
                return {ApplyStatus::Unsupported, "removing arbitrary additional-save keys is not supported by Container::readAdditionalSaveData", current->revision};
            }
        }

        if (items_seen && (!patch.inventory_updates.empty() || !patch.inventory_removals.empty()))
            return {ApplyStatus::InvalidPatch, "Items and per-slot inventory changes cannot be combined", current->revision};

        const bool has_inventory_changes =
            items_seen || !patch.inventory_updates.empty() ||
            !patch.inventory_removals.empty();
        if (has_inventory_changes &&
            (plan.custom_name || !plan.additional_updates.empty())) {
            return {ApplyStatus::Unsupported,
                    "inventory and other block-actor NBT changes are not atomic; apply them separately",
                    current->revision};
        }

        for (const auto &[slot, item_patch] : patch.inventory_updates) {
            if (slot < 0 || slot >= access->container_size)
                return {ApplyStatus::InvalidPatch, "inventory slot out of range", current->revision};
            if (patch.inventory_removals.contains(slot))
                return {ApplyStatus::InvalidPatch, "an inventory slot cannot be updated and removed in one patch", current->revision};
            std::string validation_error;
            if (!validateNbtPayload(item_patch.item, &validation_error)) {
                return {ApplyStatus::InvalidPatch,
                        "invalid inventory item NBT for slot " + std::to_string(slot) + ": " + validation_error,
                        current->revision};
            }
            auto stack = itemFromNbt(item_patch.item);
            if (!stack) return {ApplyStatus::InvalidPatch, "invalid canonical item NBT", current->revision};
            std::string item_error;
            if (!validateContainerItem(*access->container, actor_type, *stack, item_error)) {
                return {ApplyStatus::InvalidPatch,
                        "slot " + std::to_string(slot) + ": " + item_error,
                        current->revision};
            }
            plan.inventory_updates.emplace_back(slot, std::move(*stack));
        }
        for (int slot : patch.inventory_removals) {
            if (slot < 0 || slot >= access->container_size)
                return {ApplyStatus::InvalidPatch, "inventory slot out of range", current->revision};
            plan.inventory_removals.push_back(slot);
        }

        // Build and validate the final container projection before mutating any
        // live object. Invalid input must not leave a partial inventory write.
        auto candidate = captureCanonicalActorTag(*access, patch.location, server_.getMinecraftVersion());
        if (plan.custom_name) {
            if (plan.custom_name->empty()) candidate.remove("CustomName");
            else candidate.putString("CustomName", *plan.custom_name);
        }
        for (const auto &[key, value] : plan.additional_updates)
            candidate.put(key, toNativeTag(value));

        ItemProjection originals;
        if (has_inventory_changes) {
            for (int slot = 0; slot < access->container_size; ++slot) {
                const auto &stack = access->container->getItem(slot);
                if (!stack.isNull()) {
                    auto serialized = ItemStack(stack);
                    flattenNativeStorageItem(serialized);
                    originals.emplace(slot, std::move(serialized));
                }
            }
        }

        std::optional<ItemProjection> final_items;
        std::set<int> touched_slots;
        if (has_inventory_changes) {
            final_items.emplace();
            if (plan.replacement_items) {
                for (int slot = 0; slot < access->container_size; ++slot) touched_slots.insert(slot);
                for (const auto &[slot, stack] : *plan.replacement_items) {
                    if (!stack.isNull()) {
                        final_items->erase(slot);
                        final_items->emplace(slot, stack);
                    }
                }
            } else {
                *final_items = originals;
            }
            for (const auto &[slot, stack] : plan.inventory_updates) {
                touched_slots.insert(slot);
                if (stack.isNull()) final_items->erase(slot);
                else {
                    final_items->erase(slot);
                    final_items->emplace(slot, stack);
                }
            }
            for (int slot : plan.inventory_removals) {
                touched_slots.insert(slot);
                final_items->erase(slot);
            }

            ListTag items;
            for (const auto &[slot, stack] : *final_items) {
                auto item_tag = makeItemTag(slot, stack);
                items.add(item_tag.copy());
            }
            candidate.put("Items", items.copy());
        }
        if (!access->main->validateData(candidate))
            return {ApplyStatus::AdapterError, "block actor rejected the resulting canonical NBT", current->revision};

        std::set<int> write_slots = touched_slots;
        std::set<int> all_slots;
        if (final_items) {
            for (int slot = 0; slot < access->container_size; ++slot)
                all_slots.insert(slot);
        }
        std::unique_ptr<NativeStorageItemTransaction> requested_storage;
        std::unique_ptr<NativeStorageItemTransaction> rollback_storage;
        bool needs_storage_lifetimes = false;
        if (final_items) {
            for (const auto &[slot, stack] : *final_items) {
                if (hasSerializedNativeStorageContents(stack)) {
                    needs_storage_lifetimes = true;
                    write_slots.insert(slot);
                }
            }
            for (const auto &[slot, stack] : originals) {
                if (hasSerializedNativeStorageContents(stack)) {
                    needs_storage_lifetimes = true;
                }
            }

            if (needs_storage_lifetimes) {
                requested_storage =
                    std::make_unique<NativeStorageItemTransaction>(*access->level);
                rollback_storage =
                    std::make_unique<NativeStorageItemTransaction>(*access->level);
                if (!requested_storage->ready() || !rollback_storage->ready()) {
                    return {ApplyStatus::AdapterError,
                            "the exact BDS storage-item tracker is unavailable",
                            current->revision};
                }
                for (auto &[slot, stack] : *final_items) {
                    if (hasSerializedNativeStorageContents(stack) &&
                        !requested_storage->materialize(stack)) {
                        return {touched_slots.contains(slot)
                                    ? ApplyStatus::InvalidPatch
                                    : ApplyStatus::AdapterError,
                                "bundle contents in slot " +
                                    std::to_string(slot) +
                                    " could not be materialized",
                                current->revision};
                    }
                }
                for (auto &[slot, stack] : originals) {
                    if (hasSerializedNativeStorageContents(stack) &&
                        !rollback_storage->materialize(stack)) {
                        return {ApplyStatus::AdapterError,
                                "the original bundle in slot " +
                                    std::to_string(slot) +
                                    " could not be prepared for rollback",
                                current->revision};
                    }
                }
            }
        }

        // readAdditionalSaveData expects a complete save projection, not a
        // sparse tag. Passing only changed keys can reset unrelated fields.
        if (!final_items) {
            try {
                if (!plan.additional_updates.empty())
                    access->container->readAdditionalSaveData(candidate);
                if (plan.custom_name)
                    access->container->setCustomName(*plan.custom_name);
                signalContainerChanged(*access, {});
            }
            catch (...) {
                return {ApplyStatus::AdapterError,
                        "block-actor NBT write failed", current->revision};
            }

            std::optional<BlockSnapshot> updated;
            try {
                updated = capture(patch.location);
            }
            catch (...) {
            }
            return {ApplyStatus::Applied,
                    updated
                        ? "applied canonical block-actor NBT through exact BDS 26.30 adapter"
                        : "block-actor NBT was applied, but readback capture was unavailable",
                    updated ? updated->revision : 0};
        }

        if (needs_storage_lifetimes &&
            !requested_storage->escrowContainerLifetimes(
                *access->container, *rollback_storage)) {
            return {ApplyStatus::AdapterError,
                    "bundle lifetime escrow could not be installed before mutation",
                    current->revision};
        }

        bool requested_matches = false;
        bool requested_lifetimes_installed = false;
        try {
            for (int slot : write_slots) {
                const auto it = final_items->find(slot);
                access->container->setItem(
                    slot,
                    it == final_items->end()
                        ? ItemStack::EMPTY_ITEM
                        : it->second);
            }
            requested_matches = containerMatches(
                *access->container, access->container_size, *final_items);
            requested_lifetimes_installed =
                !needs_storage_lifetimes ||
                (requested_matches &&
                 requested_storage->replaceContainerLifetimes(
                     *access->container));
        }
        catch (...) {
            requested_matches = false;
            requested_lifetimes_installed = false;
        }

        if (!requested_matches || !requested_lifetimes_installed) {
            bool restored = false;
            bool rollback_lifetimes_installed = !needs_storage_lifetimes;
            try {
                // Restore the complete projection. Special containers can
                // update neighboring slots as a side effect of one setItem.
                for (int slot : all_slots) {
                    const auto it = originals.find(slot);
                    access->container->setItem(
                        slot,
                        it == originals.end()
                            ? ItemStack::EMPTY_ITEM
                            : it->second);
                }
                restored = containerMatches(
                    *access->container, access->container_size, originals);
                if (needs_storage_lifetimes && restored) {
                    rollback_lifetimes_installed =
                        rollback_storage->replaceContainerLifetimes(
                            *access->container);
                }
            }
            catch (...) {
                restored = false;
            }

            // If restoration or cleanup failed, the preinstalled owner escrow
            // intentionally remains as the safe union of the original,
            // requested, and rollback managers. Local tracker destruction can
            // therefore never strand a live bundle stack.
            try {
                signalContainerChanged(*access, all_slots);
            }
            catch (...) {
            }

            std::uint64_t rolled_back_revision = restored
                                                      ? current->revision
                                                      : 0;
            try {
                if (auto rolled_back = capture(patch.location))
                    rolled_back_revision = rolled_back->revision;
            }
            catch (...) {
            }
            return {ApplyStatus::AdapterError,
                    restored && rollback_lifetimes_installed
                        ? "container rejected or canonicalized the requested item; the complete original inventory was restored"
                        : "container rejected the requested item; rollback was incomplete, so all bundle lifetimes remain safely escrowed",
                    rolled_back_revision};
        }

        try {
            signalContainerChanged(*access, write_slots);
        }
        catch (...) {
            // The mutation and lifetime transfer are already committed. A
            // notification failure must not be reported as a safe-to-retry
            // write failure.
        }

        std::optional<BlockSnapshot> updated;
        try {
            updated = capture(patch.location);
        }
        catch (...) {
        }
        return {ApplyStatus::Applied,
                updated
                    ? "applied canonical block-actor NBT through exact BDS 26.30 adapter"
                    : "container inventory was applied, but readback capture was unavailable",
                updated ? updated->revision : 0};
    }

    bool markBlockActorDirty(const BlockLocation &location) override {
        auto lookup = locateActor(server_, location);
        auto access = std::move(lookup.access);
        if (!access) return false;
        access->main->setChanged();
        access->main->onChanged(*access->source);
        return true;
    }

    bool sendBlockActorUpdate(const BlockLocation &location) override {
        auto lookup = locateActor(server_, location);
        auto access = std::move(lookup.access);
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
