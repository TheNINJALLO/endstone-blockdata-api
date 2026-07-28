#include "endstone_blockdata/bds_26_30_player_inventory_adapter.h"
#include "endstone_blockdata/bds_26_30_adapter.h"
#include "native_item_bridge.h"

#include <endstone/endstone.hpp>
#include "endstone/core/player.h"

#include "bedrock/nbt/compound_tag.h"
#include "bedrock/world/actor/armor_slot.h"
#include "bedrock/world/actor/player/player.h"
#include "bedrock/world/container.h"
#include "bedrock/world/item/item.h"
#include "bedrock/world/item/item_stack.h"
#include "bedrock/world/level/level.h"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <initializer_list>
#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

namespace endstone_blockdata {
namespace {

bool isExactRuntimeBuild(const endstone::Server &server)
{
    return isExpectedBds2630Build(
               server.getMinecraftVersion(), ENDSTONE_BLOCKDATA_BDS_BUILD) &&
           isExpectedEndstoneVersion(
               server.getVersion(), ENDSTONE_BLOCKDATA_ENDSTONE_VERSION);
}

const NbtCompound *compoundOf(const NbtValue &value)
{
    const auto *ptr = std::get_if<NbtValue::CompoundPtr>(&value.value);
    return ptr && *ptr ? ptr->get() : nullptr;
}

const NbtList *listOf(const NbtValue &value)
{
    const auto *ptr = std::get_if<NbtValue::ListPtr>(&value.value);
    return ptr && *ptr ? ptr->get() : nullptr;
}

const NbtValue *field(
    const NbtCompound &compound,
    std::initializer_list<std::string_view> keys)
{
    for (const auto key : keys) {
        const auto it = compound.find(std::string(key));
        if (it != compound.end()) return &it->second;
    }
    return nullptr;
}

std::optional<std::string> stringField(
    const NbtCompound &compound,
    std::initializer_list<std::string_view> keys)
{
    if (const auto *value = field(compound, keys)) {
        if (const auto *text = std::get_if<std::string>(&value->value)) return *text;
    }
    return std::nullopt;
}

std::int32_t intValue(const NbtValue &value, std::int32_t fallback = 0)
{
    return std::visit(
        [fallback](const auto &entry) -> std::int32_t {
            using T = std::decay_t<decltype(entry)>;
            if constexpr (std::is_same_v<T, bool>) return entry ? 1 : 0;
            else if constexpr (
                std::is_same_v<T, std::int8_t> ||
                std::is_same_v<T, std::int16_t> ||
                std::is_same_v<T, std::int32_t> ||
                std::is_same_v<T, std::int64_t>) {
                if (entry > std::numeric_limits<std::int32_t>::max() ||
                    entry < std::numeric_limits<std::int32_t>::min()) {
                    return fallback;
                }
                return static_cast<std::int32_t>(entry);
            }
            return fallback;
        },
        value.value);
}

std::optional<std::int64_t> integerValue(const NbtValue &value)
{
    return std::visit(
        [](const auto &entry) -> std::optional<std::int64_t> {
            using T = std::decay_t<decltype(entry)>;
            if constexpr (
                std::is_same_v<T, std::int8_t> ||
                std::is_same_v<T, std::int16_t> ||
                std::is_same_v<T, std::int32_t> ||
                std::is_same_v<T, std::int64_t>) {
                return static_cast<std::int64_t>(entry);
            }
            return std::nullopt;
        },
        value.value);
}

NbtValue fromNativeTag(const Tag &tag)
{
    switch (tag.getId()) {
    case Tag::Type::End: return {};
    case Tag::Type::Byte:
        return static_cast<std::int8_t>(static_cast<const ByteTag &>(tag).data);
    case Tag::Type::Short: return static_cast<const ShortTag &>(tag).data;
    case Tag::Type::Int: return static_cast<const IntTag &>(tag).data;
    case Tag::Type::Int64: return static_cast<const Int64Tag &>(tag).data;
    case Tag::Type::Float: return static_cast<const FloatTag &>(tag).data;
    case Tag::Type::Double: return static_cast<const DoubleTag &>(tag).data;
    case Tag::Type::String: return static_cast<const StringTag &>(tag).data;
    case Tag::Type::ByteArray: {
        ByteArray output;
        for (const auto value : static_cast<const ByteArrayTag &>(tag).data) {
            output.push_back(static_cast<std::int8_t>(value));
        }
        return output;
    }
    case Tag::Type::IntArray: return static_cast<const IntArrayTag &>(tag).data;
    case Tag::Type::List: {
        const auto &list = static_cast<const ListTag &>(tag);
        NbtList output;
        output.reserve(list.size());
        for (std::size_t index = 0; index < list.size(); ++index) {
            if (const auto *entry = list.get(static_cast<int>(index))) {
                output.push_back(fromNativeTag(*entry));
            }
        }
        return NbtValue::list(std::move(output));
    }
    case Tag::Type::Compound: {
        const auto &compound = static_cast<const CompoundTag &>(tag);
        NbtCompound output;
        for (const auto &[key, entry] : compound) {
            if (const auto *value = entry.get()) {
                output.emplace(key, fromNativeTag(*value));
            }
        }
        return NbtValue::compound(std::move(output));
    }
    default: return {};
    }
}

std::unique_ptr<Tag> toNativeTag(const NbtValue &value)
{
    return std::visit(
        [](const auto &entry) -> std::unique_ptr<Tag> {
            using T = std::decay_t<decltype(entry)>;
            if constexpr (std::is_same_v<T, std::monostate>) {
                return std::make_unique<EndTag>();
            }
            else if constexpr (std::is_same_v<T, bool>) {
                return std::make_unique<ByteTag>(entry ? 1 : 0);
            }
            else if constexpr (std::is_same_v<T, std::int8_t>) {
                return std::make_unique<ByteTag>(static_cast<std::uint8_t>(entry));
            }
            else if constexpr (std::is_same_v<T, std::int16_t>) {
                return std::make_unique<ShortTag>(entry);
            }
            else if constexpr (std::is_same_v<T, std::int32_t>) {
                return std::make_unique<IntTag>(entry);
            }
            else if constexpr (std::is_same_v<T, std::int64_t>) {
                return std::make_unique<Int64Tag>(entry);
            }
            else if constexpr (std::is_same_v<T, float>) {
                return std::make_unique<FloatTag>(entry);
            }
            else if constexpr (std::is_same_v<T, double>) {
                return std::make_unique<DoubleTag>(entry);
            }
            else if constexpr (std::is_same_v<T, std::string>) {
                return std::make_unique<StringTag>(entry);
            }
            else if constexpr (std::is_same_v<T, ByteArray>) {
                ByteArrayTag::ArrayData data;
                data.reserve(entry.size());
                for (const auto value : entry) data.push_back(static_cast<char>(value));
                return std::make_unique<ByteArrayTag>(std::move(data));
            }
            else if constexpr (std::is_same_v<T, IntArray>) {
                return std::make_unique<IntArrayTag>(entry);
            }
            else if constexpr (std::is_same_v<T, LongArray>) {
                auto list = std::make_unique<ListTag>();
                for (const auto value : entry) list->add(std::make_unique<Int64Tag>(value));
                return list;
            }
            else if constexpr (std::is_same_v<T, NbtValue::ListPtr>) {
                auto list = std::make_unique<ListTag>();
                if (entry) {
                    for (const auto &value : *entry) list->add(toNativeTag(value));
                }
                return list;
            }
            else if constexpr (std::is_same_v<T, NbtValue::CompoundPtr>) {
                auto compound = std::make_unique<CompoundTag>();
                if (entry) {
                    for (const auto &[key, value] : *entry) {
                        compound->put(key, toNativeTag(value));
                    }
                }
                return compound;
            }
        },
        value.value);
}

std::unique_ptr<CompoundTag> toNativeCompound(const NbtValue &value)
{
    auto tag = toNativeTag(value);
    if (!tag || tag->getId() != Tag::Type::Compound) return {};
    return std::unique_ptr<CompoundTag>(
        static_cast<CompoundTag *>(tag.release()));
}

CompoundTag makeItemTag(std::int32_t slot, const ItemStack &item)
{
    CompoundTag output;
    output.putByte("Slot", static_cast<std::uint8_t>(slot));
    const auto *definition = item.getItem();
    output.putString(
        "Name", definition ? definition->getFullItemName() : item.getName());
    output.putByte("Count", item.getCount());
    output.putShort("Damage", item.getDamageValue());
    output.putShort("Aux", item.getAuxValue());
    output.putShort("LegacyId", item.getId());
    if (!item.getCustomName().empty()) {
        output.putString("CustomName", item.getCustomName());
    }
    if (const auto *user_data = item.getUserData()) {
        output.putCompound("tag", user_data->clone());
    }

    if (!item.getCanPlaceOn().empty()) {
        ListTag list;
        for (const auto *type : item.getCanPlaceOn()) {
            if (type) list.add(std::make_unique<StringTag>(type->getName().getString()));
        }
        output.put("CanPlaceOn", list.copy());
    }
    if (!item.getCanDestroy().empty()) {
        ListTag list;
        for (const auto *type : item.getCanDestroy()) {
            if (type) list.add(std::make_unique<StringTag>(type->getName().getString()));
        }
        output.put("CanDestroy", list.copy());
    }
    return output;
}

NbtValue itemSnapshot(std::int32_t slot, const ItemStack &item)
{
    if (item.isNull()) {
        return NbtValue::compound(
            {{"Slot", slot}, {"empty", true}});
    }
    return fromNativeTag(makeItemTag(slot, item));
}

std::vector<std::string> stringListField(
    const NbtCompound &compound,
    std::initializer_list<std::string_view> keys)
{
    std::vector<std::string> output;
    const auto *value = field(compound, keys);
    const auto *list = value ? listOf(*value) : nullptr;
    if (!list) return output;
    for (const auto &entry : *list) {
        if (const auto *text = std::get_if<std::string>(&entry.value)) {
            output.push_back(*text);
        }
    }
    return output;
}

std::optional<ItemStack> itemFromNbt(const NbtValue &value)
{
    const auto *item = compoundOf(value);
    if (!item) return std::nullopt;
    if (const auto *empty = field(*item, {"empty"});
        empty && intValue(*empty, 0) != 0) {
        return ItemStack::EMPTY_ITEM;
    }

    const auto name = stringField(*item, {"Name", "name", "id"});
    if (!name || name->empty()) return std::nullopt;

    std::int32_t count = 1;
    if (const auto *count_value = field(*item, {"Count", "count"})) {
        const auto parsed = integerValue(*count_value);
        if (!parsed || *parsed < 1 ||
            *parsed > std::numeric_limits<std::uint8_t>::max()) {
            return std::nullopt;
        }
        count = static_cast<std::int32_t>(*parsed);
    }

    std::int32_t aux = 0;
    if (const auto *aux_value = field(*item, {"Damage", "Aux", "aux"})) {
        const auto parsed = integerValue(*aux_value);
        if (!parsed || *parsed < std::numeric_limits<std::int16_t>::min() ||
            *parsed > std::numeric_limits<std::int16_t>::max()) {
            return std::nullopt;
        }
        aux = static_cast<std::int32_t>(*parsed);
    }

    std::unique_ptr<CompoundTag> user_data;
    if (const auto *tag = field(*item, {"tag", "user_data"})) {
        user_data = toNativeCompound(*tag);
        if (!user_data) return std::nullopt;
    }

    ItemStack stack(*name, count, aux, user_data.get());
    if (stack.isNull() || count > stack.getMaxStackSize()) return std::nullopt;

    const auto can_place = stringListField(*item, {"CanPlaceOn", "can_place_on"});
    if (!can_place.empty() && !stack.setCanPlaceOn(can_place)) return std::nullopt;
    const auto can_destroy = stringListField(*item, {"CanDestroy", "can_destroy"});
    if (!can_destroy.empty() && !stack.setCanDestroy(can_destroy)) return std::nullopt;
    return stack;
}

void captureContainer(
    const Container &container,
    std::vector<PlayerInventoryItemSnapshot> &output,
    std::int32_t &capacity)
{
    constexpr std::int32_t MaxPlayerContainerSlots = 4096;
    capacity = container.getContainerSize();
    if (capacity < 0 || capacity > MaxPlayerContainerSlots) {
        capacity = 0;
        return;
    }
    output.clear();
    output.reserve(static_cast<std::size_t>(capacity));
    for (std::int32_t slot = 0; slot < capacity; ++slot) {
        const auto &item = container.getItem(slot);
        if (item.isNull()) continue;
        auto nbt = itemSnapshot(slot, item);
        output.push_back({slot, std::move(nbt), 0});
        output.back().revision = hashNbt(output.back().item);
    }
}

void captureSingle(
    const ItemStack &item,
    std::vector<PlayerInventoryItemSnapshot> &output,
    std::int32_t slot = 0)
{
    output.clear();
    if (item.isNull()) return;
    auto nbt = itemSnapshot(slot, item);
    output.push_back({slot, std::move(nbt), 0});
    output.back().revision = hashNbt(output.back().item);
}

using NativeUpdates = std::map<std::int32_t, ItemStack>;

bool parseUpdates(
    const std::map<std::int32_t, PlayerInventoryItemSnapshot> &source,
    std::int32_t capacity,
    NativeUpdates &output,
    std::string &error)
{
    output.clear();
    for (const auto &[slot, item] : source) {
        if (slot < 0 || slot >= capacity) {
            error = "slot " + std::to_string(slot) + " is outside the section capacity";
            return false;
        }
        auto stack = itemFromNbt(item.item);
        if (!stack) {
            error = "slot " + std::to_string(slot) + " contains invalid item NBT";
            return false;
        }
        output.emplace(slot, std::move(*stack));
    }
    return true;
}

bool validateRemovals(
    const std::set<std::int32_t> &removals,
    std::int32_t capacity,
    std::string &error)
{
    for (const auto slot : removals) {
        if (slot < 0 || slot >= capacity) {
            error = "slot " + std::to_string(slot) + " is outside the section capacity";
            return false;
        }
    }
    return true;
}

void applyContainerChanges(
    Container &container,
    NativeUpdates &updates,
    const std::set<std::int32_t> &removals)
{
    for (auto &[slot, item] : updates) {
        container.setItem(slot, item);
        container.setContainerChanged(slot);
    }
    for (const auto slot : removals) {
        container.setItem(slot, ItemStack::EMPTY_ITEM);
        container.setContainerChanged(slot);
    }
}

class Bds2630PlayerInventoryAdapter final : public IPlayerInventoryAdapter {
public:
    explicit Bds2630PlayerInventoryAdapter(endstone::Server &server)
        : server_(server)
    {
    }

    [[nodiscard]] std::string_view name() const noexcept override
    {
        return "bds-26.30-exact-player-inventory";
    }

    [[nodiscard]] bool verify() const noexcept
    {
        try {
            return sizeof(void *) == 8 && isExactRuntimeBuild(server_);
        }
        catch (...) {
            return false;
        }
    }

    [[nodiscard]] std::optional<PlayerInventorySnapshot> capture(
        endstone::Player &player) override
    {
        if (!server_.isPrimaryThread() || !isExactRuntimeBuild(server_)) {
            return std::nullopt;
        }

        auto *exact = dynamic_cast<endstone::core::EndstonePlayer *>(&player);
        if (!exact || !exact->isValid()) return std::nullopt;
        auto &native = exact->getHandle();

        PlayerInventorySnapshot snapshot;
        snapshot.player_name = player.getName();
        snapshot.xuid = player.getXuid();
        snapshot.selected_hotbar_slot = native.getSelectedItemSlot();

        captureContainer(
            native.getInventory(), snapshot.main, snapshot.main_size);

        snapshot.armor_size = 4;
        snapshot.armor.clear();
        for (std::int32_t slot = 0; slot < snapshot.armor_size; ++slot) {
            const auto &item = native.getArmor(static_cast<ArmorSlot>(slot));
            if (item.isNull()) continue;
            auto nbt = itemSnapshot(slot, item);
            snapshot.armor.push_back({slot, std::move(nbt), 0});
            snapshot.armor.back().revision = hashNbt(snapshot.armor.back().item);
        }

        snapshot.offhand_size = 1;
        captureSingle(native.getOffhandSlot(), snapshot.offhand);

        if (const auto *ender = native.getEnderChestContainer()) {
            captureContainer(
                *ender, snapshot.ender_chest, snapshot.ender_chest_size);
        }

        snapshot.revision = calculatePlayerInventoryRevision(snapshot);
        return snapshot;
    }

    ApplyResult apply(
        endstone::Player &player,
        const PlayerInventoryPatch &patch,
        ConflictPolicy policy) override
    {
        if (!server_.isPrimaryThread()) {
            return {ApplyStatus::AdapterError,
                    "live player inventory apply must run on the primary thread", 0};
        }
        if (!isExactRuntimeBuild(server_)) {
            return {ApplyStatus::Unsupported,
                    "player inventory adapter requires BDS " ENDSTONE_BLOCKDATA_BDS_BUILD
                    " with Endstone " ENDSTONE_BLOCKDATA_ENDSTONE_VERSION,
                    0};
        }
        if (policy != ConflictPolicy::FailIfChanged && policy != ConflictPolicy::Force) {
            return {ApplyStatus::Unsupported,
                    "player inventory supports only FailIfChanged and Force", 0};
        }

        auto current = capture(player);
        if (!current) {
            return {ApplyStatus::AdapterError,
                    "player is unavailable or no longer connected", 0};
        }
        if (patch.expected_revision && policy != ConflictPolicy::Force &&
            *patch.expected_revision != current->revision) {
            return {ApplyStatus::Conflict, "player inventory revision changed",
                    current->revision};
        }

        auto *exact = dynamic_cast<endstone::core::EndstonePlayer *>(&player);
        if (!exact || !exact->isValid()) {
            return {ApplyStatus::AdapterError,
                    "player is unavailable or no longer connected", current->revision};
        }
        auto &native = exact->getHandle();
        auto &main = native.getInventory();
        auto *ender = native.getEnderChestContainer();

        NativeItemRegistryScope registry_scope(native.getLevel());
        NativeUpdates main_updates;
        NativeUpdates armor_updates;
        NativeUpdates offhand_updates;
        NativeUpdates ender_updates;
        std::string error;

        if (!parseUpdates(patch.main_updates, current->main_size, main_updates, error) ||
            !validateRemovals(patch.main_removals, current->main_size, error)) {
            return {ApplyStatus::InvalidPatch, "main inventory " + error,
                    current->revision};
        }
        if (!parseUpdates(patch.armor_updates, current->armor_size, armor_updates, error) ||
            !validateRemovals(patch.armor_removals, current->armor_size, error)) {
            return {ApplyStatus::InvalidPatch, "armor " + error,
                    current->revision};
        }
        if (!parseUpdates(patch.offhand_updates, current->offhand_size, offhand_updates, error) ||
            !validateRemovals(patch.offhand_removals, current->offhand_size, error)) {
            return {ApplyStatus::InvalidPatch, "offhand " + error,
                    current->revision};
        }
        if ((!patch.ender_chest_updates.empty() || !patch.ender_chest_removals.empty()) &&
            !ender) {
            return {ApplyStatus::Unsupported,
                    "player ender chest is unavailable", current->revision};
        }
        if (ender &&
            (!parseUpdates(patch.ender_chest_updates, current->ender_chest_size,
                           ender_updates, error) ||
             !validateRemovals(patch.ender_chest_removals,
                               current->ender_chest_size, error))) {
            return {ApplyStatus::InvalidPatch, "ender chest " + error,
                    current->revision};
        }

        // Every item and slot is fully validated above. Mutations begin only
        // after the entire patch can be applied, preventing partial writes.
        applyContainerChanges(main, main_updates, patch.main_removals);

        for (auto &[slot, item] : armor_updates) {
            native.setArmor(static_cast<ArmorSlot>(slot), item);
        }
        for (const auto slot : patch.armor_removals) {
            native.setArmor(static_cast<ArmorSlot>(slot), ItemStack::EMPTY_ITEM);
        }

        if (const auto it = offhand_updates.find(0); it != offhand_updates.end()) {
            native.setOffhandSlot(it->second);
        }
        if (patch.offhand_removals.contains(0)) {
            native.setOffhandSlot(ItemStack::EMPTY_ITEM);
        }

        if (ender) {
            applyContainerChanges(*ender, ender_updates, patch.ender_chest_removals);
        }

        native.sendInventory(true);
        auto updated = capture(player);
        return {ApplyStatus::Applied,
                "applied canonical player inventory NBT through exact BDS 26.30 adapter",
                updated ? updated->revision : 0};
    }

private:
    endstone::Server &server_;
};

} // namespace

std::shared_ptr<IPlayerInventoryAdapter> makeBds2630PlayerInventoryAdapter(
    endstone::Server &server)
{
    auto adapter = std::make_shared<Bds2630PlayerInventoryAdapter>(server);
    return adapter->verify() ? adapter : nullptr;
}

} // namespace endstone_blockdata
