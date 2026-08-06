#include "endstone_blockdata/bds_26_40_player_inventory_adapter.h"
#include "endstone_blockdata/bds_26_40_adapter.h"
#include "native_item_bridge.h"

#include <endstone/endstone.hpp>
#include <endstone/inventory/inventory.h>
#include <endstone/inventory/item_stack.h>
#include <endstone/inventory/player_inventory.h>
#include <endstone/nbt/tag.h>

#include <cstddef>
#include <cstdint>
#include <exception>
#include <initializer_list>
#include <limits>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

namespace endstone_blockdata {
namespace {

constexpr std::int32_t MaxPlayerContainerSlots = 4096;

bool isExactRuntimeBuild(const endstone::Server &server)
{
    return isExpectedBds2640Build(
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

bool isVanillaBundleIdentifier(std::string_view identifier)
{
    constexpr std::string_view prefix = "minecraft:";
    if (!identifier.starts_with(prefix)) return false;
    const auto name = identifier.substr(prefix.size());
    return name == "bundle" || name.ends_with("_bundle");
}

bool hasSerializedStorageContents(const NbtCompound &item)
{
    const auto *tag_value = field(item, {"tag", "user_data"});
    if (!tag_value) return false;
    const auto *tag = compoundOf(*tag_value);
    if (!tag) return false;
    const auto *contents = field(*tag, {"storage_item_component_content"});
    return contents && listOf(*contents);
}

bool containsStorageItemWrite(
    const std::map<std::int32_t, PlayerInventoryItemSnapshot> &updates)
{
    for (const auto &[_, snapshot] : updates) {
        const auto *item = compoundOf(snapshot.item);
        if (!item) continue;
        if (hasSerializedStorageContents(*item)) return true;
        const auto name = stringField(*item, {"Name", "name", "id"});
        if (name && isVanillaBundleIdentifier(*name)) return true;
    }
    return false;
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

NbtValue fromEndstoneTag(const endstone::nbt::Tag &tag)
{
    return tag.visit([](const auto &entry) -> NbtValue {
        using T = std::decay_t<decltype(entry)>;
        if constexpr (std::is_same_v<T, std::monostate>) {
            return {};
        }
        else if constexpr (std::is_same_v<T, endstone::ByteTag>) {
            return static_cast<std::int8_t>(entry.value());
        }
        else if constexpr (std::is_same_v<T, endstone::ShortTag>) {
            return entry.value();
        }
        else if constexpr (std::is_same_v<T, endstone::IntTag>) {
            return entry.value();
        }
        else if constexpr (std::is_same_v<T, endstone::LongTag>) {
            return entry.value();
        }
        else if constexpr (std::is_same_v<T, endstone::FloatTag>) {
            return entry.value();
        }
        else if constexpr (std::is_same_v<T, endstone::DoubleTag>) {
            return entry.value();
        }
        else if constexpr (std::is_same_v<T, endstone::StringTag>) {
            return entry.value();
        }
        else if constexpr (std::is_same_v<T, endstone::ByteArrayTag>) {
            ByteArray output;
            output.reserve(entry.size());
            for (const auto value : entry) {
                output.push_back(static_cast<std::int8_t>(value));
            }
            return output;
        }
        else if constexpr (std::is_same_v<T, endstone::IntArrayTag>) {
            IntArray output;
            output.reserve(entry.size());
            for (const auto value : entry) output.push_back(value);
            return output;
        }
        else if constexpr (std::is_same_v<T, endstone::ListTag>) {
            NbtList output;
            output.reserve(entry.size());
            for (const auto &value : entry) output.push_back(fromEndstoneTag(value));
            return NbtValue::list(std::move(output));
        }
        else if constexpr (std::is_same_v<T, endstone::CompoundTag>) {
            NbtCompound output;
            for (const auto &[key, value] : entry) {
                output.emplace(key, fromEndstoneTag(value));
            }
            return NbtValue::compound(std::move(output));
        }
    });
}

endstone::nbt::Tag toEndstoneTag(const NbtValue &value)
{
    return std::visit(
        [](const auto &entry) -> endstone::nbt::Tag {
            using T = std::decay_t<decltype(entry)>;
            if constexpr (std::is_same_v<T, std::monostate>) {
                return {};
            }
            else if constexpr (std::is_same_v<T, bool>) {
                return endstone::ByteTag(static_cast<std::uint8_t>(entry ? 1 : 0));
            }
            else if constexpr (std::is_same_v<T, std::int8_t>) {
                return endstone::ByteTag(static_cast<std::uint8_t>(entry));
            }
            else if constexpr (std::is_same_v<T, std::int16_t>) {
                return endstone::ShortTag(entry);
            }
            else if constexpr (std::is_same_v<T, std::int32_t>) {
                return endstone::IntTag(entry);
            }
            else if constexpr (std::is_same_v<T, std::int64_t>) {
                return endstone::LongTag(entry);
            }
            else if constexpr (std::is_same_v<T, float>) {
                return endstone::FloatTag(entry);
            }
            else if constexpr (std::is_same_v<T, double>) {
                return endstone::DoubleTag(entry);
            }
            else if constexpr (std::is_same_v<T, std::string>) {
                return endstone::StringTag(entry);
            }
            else if constexpr (std::is_same_v<T, ByteArray>) {
                endstone::ByteArrayTag::storage_type output;
                output.reserve(entry.size());
                for (const auto byte : entry) {
                    output.push_back(static_cast<std::uint8_t>(byte));
                }
                return endstone::ByteArrayTag(std::move(output));
            }
            else if constexpr (std::is_same_v<T, IntArray>) {
                return endstone::IntArrayTag(
                    endstone::IntArrayTag::storage_type(entry.begin(), entry.end()));
            }
            else if constexpr (std::is_same_v<T, LongArray>) {
                endstone::ListTag output;
                for (const auto number : entry) {
                    output.emplace_back(endstone::LongTag(number));
                }
                return output;
            }
            else if constexpr (std::is_same_v<T, NbtValue::ListPtr>) {
                endstone::ListTag output;
                if (entry) {
                    for (const auto &child : *entry) {
                        output.emplace_back(toEndstoneTag(child));
                    }
                }
                return output;
            }
            else if constexpr (std::is_same_v<T, NbtValue::CompoundPtr>) {
                endstone::CompoundTag output;
                if (entry) {
                    for (const auto &[key, child] : *entry) {
                        output.emplace(key, toEndstoneTag(child));
                    }
                }
                return output;
            }
        },
        value.value);
}

std::optional<endstone::CompoundTag> toEndstoneCompound(const NbtValue &value)
{
    auto tag = toEndstoneTag(value);
    const auto *compound = tag.get_if<endstone::CompoundTag>();
    if (!compound) return std::nullopt;
    return *compound;
}

NbtValue itemSnapshot(std::int32_t slot, const endstone::ItemStack &item)
{
    auto serialized = item;
    if (!flattenEndstoneStorageItem(serialized)) {
        throw std::runtime_error(
            "BDS 1.26.40 storage-item clone flatten failed");
    }

    NbtCompound output;
    output.emplace("Slot", slot);
    output.emplace("Name", static_cast<std::string>(serialized.getType().getId()));
    output.emplace("Count", static_cast<std::int32_t>(serialized.getAmount()));
    output.emplace("Damage", static_cast<std::int32_t>(serialized.getData()));
    output.emplace("Aux", static_cast<std::int32_t>(serialized.getData()));

    const auto user_data = serialized.getNbt();
    if (!user_data.empty()) {
        output.emplace(
            "tag", fromEndstoneTag(endstone::nbt::Tag(user_data)));
    }
    return NbtValue::compound(std::move(output));
}

bool itemFromNbt(
    const NbtValue &value,
    const std::optional<endstone::ItemStack> &existing,
    std::optional<endstone::ItemStack> &output)
{
    output.reset();
    const auto *item = compoundOf(value);
    if (!item) return false;
    if (const auto *empty = field(*item, {"empty"});
        empty && intValue(*empty, 0) != 0) {
        return true;
    }

    const auto name = stringField(*item, {"Name", "name", "id"});
    if (!name || name->empty()) return false;
    if (isVanillaBundleIdentifier(*name) &&
        !hasSerializedStorageContents(*item)) {
        return false;
    }

    std::int32_t count = 1;
    if (const auto *count_value = field(*item, {"Count", "count"})) {
        const auto parsed = integerValue(*count_value);
        if (!parsed || *parsed < 1 ||
            *parsed > std::numeric_limits<std::uint8_t>::max()) {
            return false;
        }
        count = static_cast<std::int32_t>(*parsed);
    }

    std::int32_t aux = 0;
    if (const auto *aux_value = field(*item, {"Damage", "Aux", "aux"})) {
        const auto parsed = integerValue(*aux_value);
        if (!parsed || *parsed < std::numeric_limits<std::int16_t>::min() ||
            *parsed > std::numeric_limits<std::int16_t>::max()) {
            return false;
        }
        aux = static_cast<std::int32_t>(*parsed);
    }

    try {
        std::optional<endstone::ItemStack> stack;
        if (existing && !isVanillaBundleIdentifier(*name) &&
            !hasSerializedStorageContents(*item) &&
            static_cast<std::string>(existing->getType().getId()) == *name) {
            // Copying the existing Endstone item preserves Bedrock fields that
            // are not exposed by the public API, such as adventure-mode
            // CanPlaceOn and CanDestroy lists. Bundle user NBT is replaced below.
            stack.emplace(*existing);
        }
        else {
            stack.emplace(endstone::ItemTypeId(*name), count, aux);
        }

        stack->setAmount(count);
        stack->setData(aux);
        if (count > stack->getMaxStackSize()) return false;

        if (const auto *tag = field(*item, {"tag", "user_data"})) {
            auto user_data = toEndstoneCompound(*tag);
            if (!user_data) return false;
            stack->setNbt(*user_data);
        }
        else {
            stack->setNbt({});
        }

        output.emplace(std::move(*stack));
        return true;
    }
    catch (...) {
        return false;
    }
}

void captureInventory(
    const endstone::Inventory &inventory,
    std::vector<PlayerInventoryItemSnapshot> &output,
    std::int32_t &capacity)
{
    capacity = inventory.getSize();
    if (capacity < 0 || capacity > MaxPlayerContainerSlots) {
        capacity = 0;
        output.clear();
        return;
    }

    output.clear();
    output.reserve(static_cast<std::size_t>(capacity));
    for (std::int32_t slot = 0; slot < capacity; ++slot) {
        const auto item = inventory.getItem(slot);
        if (!item) continue;
        auto nbt = itemSnapshot(slot, *item);
        output.push_back({slot, std::move(nbt), 0});
        output.back().revision = hashNbt(output.back().item);
    }
}

void captureSingle(
    const std::optional<endstone::ItemStack> &item,
    std::vector<PlayerInventoryItemSnapshot> &output,
    std::int32_t slot = 0)
{
    output.clear();
    if (!item) return;
    auto nbt = itemSnapshot(slot, *item);
    output.push_back({slot, std::move(nbt), 0});
    output.back().revision = hashNbt(output.back().item);
}

std::optional<endstone::ItemStack> armorItem(
    const endstone::PlayerInventory &inventory,
    std::int32_t slot)
{
    switch (slot) {
    case 0: return inventory.getHelmet();
    case 1: return inventory.getChestplate();
    case 2: return inventory.getLeggings();
    case 3: return inventory.getBoots();
    default: return std::nullopt;
    }
}

void setArmorItem(
    endstone::PlayerInventory &inventory,
    std::int32_t slot,
    std::optional<endstone::ItemStack> item)
{
    switch (slot) {
    case 0: inventory.setHelmet(std::move(item)); break;
    case 1: inventory.setChestplate(std::move(item)); break;
    case 2: inventory.setLeggings(std::move(item)); break;
    case 3: inventory.setBoots(std::move(item)); break;
    default: break;
    }
}

using PublicUpdates =
    std::map<std::int32_t, std::optional<endstone::ItemStack>>;

template <typename ExistingItemGetter>
bool parseUpdates(
    const std::map<std::int32_t, PlayerInventoryItemSnapshot> &source,
    std::int32_t capacity,
    ExistingItemGetter &&existing_item,
    PublicUpdates &output,
    std::string &error)
{
    output.clear();
    for (const auto &[slot, item] : source) {
        if (slot < 0 || slot >= capacity) {
            error = "slot " + std::to_string(slot) +
                    " is outside the section capacity";
            return false;
        }

        std::optional<endstone::ItemStack> stack;
        if (!itemFromNbt(item.item, existing_item(slot), stack)) {
            error = "slot " + std::to_string(slot) +
                    " contains invalid item NBT";
            return false;
        }
        output.emplace(slot, std::move(stack));
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
            error = "slot " + std::to_string(slot) +
                    " is outside the section capacity";
            return false;
        }
    }
    return true;
}

void applyInventoryChanges(
    endstone::Inventory &inventory,
    PublicUpdates &updates,
    const std::set<std::int32_t> &removals)
{
    for (auto &[slot, item] : updates) {
        inventory.setItem(slot, std::move(item));
    }
    for (const auto slot : removals) inventory.clear(slot);
}

class Bds2640PlayerInventoryAdapter final : public IPlayerInventoryAdapter {
public:
    explicit Bds2640PlayerInventoryAdapter(endstone::Server &server)
        : server_(server)
    {
    }

    [[nodiscard]] std::string_view name() const noexcept override
    {
        return "bds-26.40-exact-player-inventory";
    }

    [[nodiscard]] bool verify() const noexcept
    {
        try {
            return sizeof(void *) == 8 && isExactRuntimeBuild(server_) &&
                   verifyNativeStorageItemBridge();
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

        if (!player.isValid()) return std::nullopt;

        try {
            auto &inventory = player.getInventory();
            auto &ender_chest = player.getEnderChest();

            PlayerInventorySnapshot snapshot;
            snapshot.player_name = player.getName();
            snapshot.xuid = player.getXuid();
            snapshot.selected_hotbar_slot = inventory.getHeldItemSlot();

            captureInventory(inventory, snapshot.main, snapshot.main_size);

            snapshot.armor_size = 4;
            snapshot.armor.clear();
            for (std::int32_t slot = 0; slot < snapshot.armor_size; ++slot) {
                const auto item = armorItem(inventory, slot);
                if (!item) continue;
                auto nbt = itemSnapshot(slot, *item);
                snapshot.armor.push_back({slot, std::move(nbt), 0});
                snapshot.armor.back().revision =
                    hashNbt(snapshot.armor.back().item);
            }

            snapshot.offhand_size = 1;
            captureSingle(inventory.getItemInOffHand(), snapshot.offhand);

            captureInventory(
                ender_chest, snapshot.ender_chest, snapshot.ender_chest_size);

            snapshot.revision = calculatePlayerInventoryRevision(snapshot);
            return snapshot;
        }
        catch (...) {
            return std::nullopt;
        }
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
                    "player inventory adapter requires BDS "
                    ENDSTONE_BLOCKDATA_BDS_BUILD " with Endstone "
                    ENDSTONE_BLOCKDATA_ENDSTONE_VERSION,
                    0};
        }
        if (policy != ConflictPolicy::FailIfChanged &&
            policy != ConflictPolicy::Force) {
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

        if (!player.isValid()) {
            return {ApplyStatus::AdapterError,
                    "player is unavailable or no longer connected",
                    current->revision};
        }

        if (containsStorageItemWrite(patch.main_updates) ||
            containsStorageItemWrite(patch.armor_updates) ||
            containsStorageItemWrite(patch.offhand_updates) ||
            containsStorageItemWrite(patch.ender_chest_updates)) {
            return {ApplyStatus::Unsupported,
                    "live player bundle/storage-item writes are disabled because Endstone's public inventory setters cannot transfer Bedrock dynamic-container lifetimes; captured contents remain readable",
                    current->revision};
        }

        auto &inventory = player.getInventory();
        auto &ender_chest = player.getEnderChest();

        PublicUpdates main_updates;
        PublicUpdates armor_updates;
        PublicUpdates offhand_updates;
        PublicUpdates ender_updates;
        std::string error;

        if (!parseUpdates(
                patch.main_updates, current->main_size,
                [&inventory](std::int32_t slot) {
                    return inventory.getItem(slot);
                },
                main_updates, error) ||
            !validateRemovals(
                patch.main_removals, current->main_size, error)) {
            return {ApplyStatus::InvalidPatch, "main inventory " + error,
                    current->revision};
        }
        if (!parseUpdates(
                patch.armor_updates, current->armor_size,
                [&inventory](std::int32_t slot) {
                    return armorItem(inventory, slot);
                },
                armor_updates, error) ||
            !validateRemovals(
                patch.armor_removals, current->armor_size, error)) {
            return {ApplyStatus::InvalidPatch, "armor " + error,
                    current->revision};
        }
        if (!parseUpdates(
                patch.offhand_updates, current->offhand_size,
                [&inventory](std::int32_t) {
                    return inventory.getItemInOffHand();
                },
                offhand_updates, error) ||
            !validateRemovals(
                patch.offhand_removals, current->offhand_size, error)) {
            return {ApplyStatus::InvalidPatch, "offhand " + error,
                    current->revision};
        }
        if (!parseUpdates(
                patch.ender_chest_updates, current->ender_chest_size,
                [&ender_chest](std::int32_t slot) {
                    return ender_chest.getItem(slot);
                },
                ender_updates, error) ||
            !validateRemovals(
                patch.ender_chest_removals,
                current->ender_chest_size, error)) {
            return {ApplyStatus::InvalidPatch, "ender chest " + error,
                    current->revision};
        }

        try {
            // Every item and slot is fully validated before mutations begin.
            applyInventoryChanges(
                inventory, main_updates, patch.main_removals);

            for (auto &[slot, item] : armor_updates) {
                setArmorItem(inventory, slot, std::move(item));
            }
            for (const auto slot : patch.armor_removals) {
                setArmorItem(inventory, slot, std::nullopt);
            }

            if (const auto it = offhand_updates.find(0);
                it != offhand_updates.end()) {
                inventory.setItemInOffHand(std::move(it->second));
            }
            if (patch.offhand_removals.contains(0)) {
                inventory.setItemInOffHand(std::nullopt);
            }

            applyInventoryChanges(
                ender_chest, ender_updates, patch.ender_chest_removals);

            // Endstone's public setters are the supported notification
            // boundary for container, armor, and offhand changes. Do not reach
            // through the private concrete player type for a second refresh:
            // its RTTI and implementation details are not exported plugin ABI.
        }
        catch (const std::exception &error) {
            return {ApplyStatus::AdapterError,
                    std::string("player inventory write failed: ") + error.what(),
                    current->revision};
        }
        catch (...) {
            return {ApplyStatus::AdapterError,
                    "player inventory write failed", current->revision};
        }

        auto updated = capture(player);
        return {ApplyStatus::Applied,
                "applied canonical player inventory NBT through exact BDS 26.40 adapter",
                updated ? updated->revision : 0};
    }

private:
    endstone::Server &server_;
};

} // namespace

std::shared_ptr<IPlayerInventoryAdapter> makeBds2640PlayerInventoryAdapter(
    endstone::Server &server)
{
    auto adapter = std::make_shared<Bds2640PlayerInventoryAdapter>(server);
    return adapter->verify() ? adapter : nullptr;
}

} // namespace endstone_blockdata
