#pragma once

#include "endstone_blockdata/nbt.h"

#include <algorithm>
#include <cstdint>
#include <functional>
#include <limits>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

namespace endstone_blockdata {

inline constexpr std::string_view StorageItemContentsKey = "storage_item_component_content";
inline constexpr std::int32_t DefaultStorageItemSlotCapacity = 64;
inline constexpr std::int32_t DefaultStorageItemMaxWeight = 64;
inline constexpr std::int32_t DefaultNestedStorageItemWeight = 4;
inline constexpr std::int32_t MaxStorageItemNestingDepth = 8;

enum class StorageItemStatus {
    Valid,
    WeightUnknown,
    NotStorageItem,
    InvalidItem,
    InvalidContents,
    DuplicateSlot,
    SlotOutOfRange,
    ForbiddenItem,
    NestedStorageDisabled,
    Overweight,
    NestingTooDeep,
};

[[nodiscard]] constexpr std::string_view storageItemStatusName(StorageItemStatus status) noexcept
{
    switch (status) {
    case StorageItemStatus::Valid: return "valid";
    case StorageItemStatus::WeightUnknown: return "weight_unknown";
    case StorageItemStatus::NotStorageItem: return "not_storage_item";
    case StorageItemStatus::InvalidItem: return "invalid_item";
    case StorageItemStatus::InvalidContents: return "invalid_contents";
    case StorageItemStatus::DuplicateSlot: return "duplicate_slot";
    case StorageItemStatus::SlotOutOfRange: return "slot_out_of_range";
    case StorageItemStatus::ForbiddenItem: return "forbidden_item";
    case StorageItemStatus::NestedStorageDisabled: return "nested_storage_disabled";
    case StorageItemStatus::Overweight: return "overweight";
    case StorageItemStatus::NestingTooDeep: return "nesting_too_deep";
    }
    return "invalid_item";
}

struct StorageItemRules {
    std::int32_t slot_capacity{DefaultStorageItemSlotCapacity};
    std::int32_t max_weight{DefaultStorageItemMaxWeight};
    std::int32_t nested_storage_item_weight{DefaultNestedStorageItemWeight};
    bool allow_nested_storage_items{true};
    bool reject_shulker_boxes{true};
    std::vector<std::string> allowed_items;
    std::vector<std::string> banned_items;
};

struct StorageItemEntry {
    std::int32_t slot{};
    NbtValue item;
    std::uint64_t revision{};
};

// Return the weight consumed by one copy of the supplied item. Returning
// std::nullopt keeps structural validation available but marks the weight as
// unknown. Native callers can resolve this from the live item definition.
using StorageItemWeightResolver = std::function<std::optional<std::int32_t>(
    std::string_view item_identifier, const NbtValue &item)>;

using MaxStackSizeResolver =
    std::function<std::optional<std::int32_t>(std::string_view item_identifier)>;

struct StorageItemValidation {
    StorageItemStatus status{StorageItemStatus::InvalidItem};
    std::string message;
    std::int32_t used_weight{};
    bool exact_weight{};

    [[nodiscard]] bool ok() const noexcept
    {
        return status == StorageItemStatus::Valid || status == StorageItemStatus::WeightUnknown;
    }
};

namespace storage_item_detail {

inline const NbtCompound *compoundOf(const NbtValue &value) noexcept
{
    const auto *ptr = std::get_if<NbtValue::CompoundPtr>(&value.value);
    return ptr && *ptr ? ptr->get() : nullptr;
}

inline NbtCompound *compoundOf(NbtValue &value) noexcept
{
    auto *ptr = std::get_if<NbtValue::CompoundPtr>(&value.value);
    return ptr && *ptr ? ptr->get() : nullptr;
}

inline const NbtList *listOf(const NbtValue &value) noexcept
{
    const auto *ptr = std::get_if<NbtValue::ListPtr>(&value.value);
    return ptr && *ptr ? ptr->get() : nullptr;
}

inline NbtList *listOf(NbtValue &value) noexcept
{
    auto *ptr = std::get_if<NbtValue::ListPtr>(&value.value);
    return ptr && *ptr ? ptr->get() : nullptr;
}

inline const NbtValue *field(
    const NbtCompound &compound,
    std::initializer_list<std::string_view> keys) noexcept
{
    for (const auto key : keys) {
        const auto it = compound.find(std::string(key));
        if (it != compound.end()) return &it->second;
    }
    return nullptr;
}

inline std::optional<std::int64_t> integerValue(const NbtValue &value) noexcept
{
    return std::visit(
        [](const auto &entry) -> std::optional<std::int64_t> {
            using T = std::decay_t<decltype(entry)>;
            if constexpr (std::is_same_v<T, bool> || std::is_same_v<T, std::int8_t> ||
                          std::is_same_v<T, std::int16_t> || std::is_same_v<T, std::int32_t> ||
                          std::is_same_v<T, std::int64_t>) {
                return static_cast<std::int64_t>(entry);
            }
            return std::nullopt;
        },
        value.value);
}

inline std::optional<std::string> stringField(
    const NbtCompound &compound,
    std::initializer_list<std::string_view> keys)
{
    if (const auto *value = field(compound, keys)) {
        if (const auto *text = std::get_if<std::string>(&value->value)) return *text;
    }
    return std::nullopt;
}

inline std::optional<std::int32_t> intField(
    const NbtCompound &compound,
    std::initializer_list<std::string_view> keys) noexcept
{
    const auto *value = field(compound, keys);
    if (!value) return std::nullopt;
    const auto parsed = integerValue(*value);
    if (!parsed || *parsed < std::numeric_limits<std::int32_t>::min() ||
        *parsed > std::numeric_limits<std::int32_t>::max()) {
        return std::nullopt;
    }
    return static_cast<std::int32_t>(*parsed);
}

inline std::optional<std::string> readItemIdentifier(const NbtValue &item)
{
    const auto *root = compoundOf(item);
    return root ? stringField(*root, {"Name", "name", "id"}) : std::nullopt;
}

inline std::optional<std::int32_t> readItemCount(const NbtValue &item) noexcept
{
    const auto *root = compoundOf(item);
    if (!root) return std::nullopt;
    const auto *value = field(*root, {"Count", "count"});
    if (!value) return 1;
    const auto parsed = integerValue(*value);
    if (!parsed || *parsed < 1 || *parsed > 255) return std::nullopt;
    return static_cast<std::int32_t>(*parsed);
}

inline const NbtList *storageContents(const NbtValue &item) noexcept
{
    const auto *root = compoundOf(item);
    if (!root) return nullptr;
    const auto *tag_value = field(*root, {"tag", "user_data"});
    const auto *tag = tag_value ? compoundOf(*tag_value) : nullptr;
    if (!tag) return nullptr;
    const auto *contents_value = field(*tag, {StorageItemContentsKey});
    return contents_value ? listOf(*contents_value) : nullptr;
}

inline bool hasStorageContentsField(const NbtValue &item) noexcept
{
    const auto *root = compoundOf(item);
    if (!root) return false;
    const auto *tag_value = field(*root, {"tag", "user_data"});
    const auto *tag = tag_value ? compoundOf(*tag_value) : nullptr;
    return tag && field(*tag, {StorageItemContentsKey}) != nullptr;
}

inline bool isShulkerBox(std::string_view identifier) noexcept
{
    constexpr std::string_view prefix = "minecraft:";
    if (!identifier.starts_with(prefix)) return false;
    const auto name = identifier.substr(prefix.size());
    return name == "shulker_box" || name == "undyed_shulker_box" ||
           name.ends_with("_shulker_box");
}

inline bool containsIdentifier(const std::vector<std::string> &values, std::string_view identifier)
{
    return std::find(values.begin(), values.end(), identifier) != values.end();
}

inline std::optional<std::int32_t> embeddedItemWeight(const NbtValue &item) noexcept
{
    const auto *root = compoundOf(item);
    if (!root) return std::nullopt;
    return intField(*root, {"_endstone_storage_weight", "StorageWeight", "storage_weight"});
}

inline std::optional<std::int32_t> embeddedMaxStackSize(const NbtValue &item) noexcept
{
    const auto *root = compoundOf(item);
    if (!root) return std::nullopt;
    return intField(*root, {"_endstone_max_stack_size", "MaxStackSize", "max_stack_size"});
}

inline StorageItemValidation invalid(
    StorageItemStatus status,
    std::string message,
    std::int32_t weight = 0,
    bool exact = false)
{
    return {status, std::move(message), weight, exact};
}

} // namespace storage_item_detail

[[nodiscard]] inline bool isVanillaBundleIdentifier(std::string_view item_identifier) noexcept
{
    constexpr std::string_view prefix = "minecraft:";
    if (!item_identifier.starts_with(prefix)) return false;
    const auto name = item_identifier.substr(prefix.size());
    return name == "bundle" || name.ends_with("_bundle");
}

[[nodiscard]] inline bool isStorageItemNbt(const NbtValue &item) noexcept
{
    const auto identifier = storage_item_detail::readItemIdentifier(item);
    return (identifier && isVanillaBundleIdentifier(*identifier)) ||
           storage_item_detail::hasStorageContentsField(item);
}

[[nodiscard]] inline std::optional<std::int32_t> storageWeightFromMaxStackSize(
    std::int32_t max_stack_size,
    std::int32_t max_weight = DefaultStorageItemMaxWeight) noexcept
{
    if (max_stack_size < 1 || max_stack_size > 255 || max_weight < 1) return std::nullopt;
    return (max_weight + max_stack_size - 1) / max_stack_size;
}

[[nodiscard]] inline StorageItemWeightResolver makeMaxStackSizeWeightResolver(
    MaxStackSizeResolver resolver,
    std::int32_t max_weight = DefaultStorageItemMaxWeight)
{
    return [resolver = std::move(resolver), max_weight](
               std::string_view identifier,
               const NbtValue &) -> std::optional<std::int32_t> {
        if (!resolver) return std::nullopt;
        const auto max_stack = resolver(identifier);
        return max_stack ? storageWeightFromMaxStackSize(*max_stack, max_weight) : std::nullopt;
    };
}

namespace storage_item_detail {

inline StorageItemValidation validateStorageItemImpl(
    const NbtValue &item,
    const StorageItemRules &rules,
    const StorageItemWeightResolver &weight_resolver,
    std::int32_t depth)
{
    if (depth > MaxStorageItemNestingDepth) {
        return invalid(
            StorageItemStatus::NestingTooDeep,
            "storage item nesting exceeds the supported depth");
    }

    const auto identifier = readItemIdentifier(item);
    if (!identifier) {
        return invalid(
            StorageItemStatus::InvalidItem,
            "storage item must be an item compound with an identifier");
    }

    const bool vanilla_bundle = isVanillaBundleIdentifier(*identifier);
    const auto *contents = storageContents(item);
    if (!contents) {
        if (hasStorageContentsField(item)) {
            return invalid(
                StorageItemStatus::InvalidContents,
                "storage_item_component_content must be an NBT list");
        }
        if (!vanilla_bundle) {
            return invalid(
                StorageItemStatus::NotStorageItem,
                "item has no storage_item_component_content list");
        }
        return {StorageItemStatus::Valid, "empty bundle", 0, true};
    }

    if (contents->size() > static_cast<std::size_t>(rules.slot_capacity)) {
        return invalid(
            StorageItemStatus::InvalidContents,
            "storage item has more entries than its slot capacity");
    }

    std::set<std::int32_t> occupied;
    std::int64_t weight = 0;
    bool exact_weight = true;

    for (const auto &entry : *contents) {
        const auto *compound = compoundOf(entry);
        if (!compound) {
            return invalid(
                StorageItemStatus::InvalidContents,
                "storage item entries must be item compounds",
                static_cast<std::int32_t>(weight),
                exact_weight);
        }

        const auto slot = intField(*compound, {"Slot", "slot"});
        if (!slot) {
            return invalid(
                StorageItemStatus::InvalidContents,
                "storage item entry is missing a valid Slot",
                static_cast<std::int32_t>(weight),
                exact_weight);
        }
        if (*slot < 0 || *slot >= rules.slot_capacity) {
            return invalid(
                StorageItemStatus::SlotOutOfRange,
                "storage item slot is outside the supported range",
                static_cast<std::int32_t>(weight),
                exact_weight);
        }
        if (!occupied.insert(*slot).second) {
            return invalid(
                StorageItemStatus::DuplicateSlot,
                "storage item contains a duplicate slot",
                static_cast<std::int32_t>(weight),
                exact_weight);
        }

        const auto nested_identifier = readItemIdentifier(entry);
        const auto count = readItemCount(entry);
        if (!nested_identifier || !count) {
            return invalid(
                StorageItemStatus::InvalidItem,
                "storage item contains an invalid item entry",
                static_cast<std::int32_t>(weight),
                exact_weight);
        }

        if (!rules.allowed_items.empty() &&
            !containsIdentifier(rules.allowed_items, *nested_identifier)) {
            return invalid(
                StorageItemStatus::ForbiddenItem,
                "item is not included in the storage item's allowed-items list",
                static_cast<std::int32_t>(weight),
                exact_weight);
        }
        if (containsIdentifier(rules.banned_items, *nested_identifier) ||
            (rules.reject_shulker_boxes && isShulkerBox(*nested_identifier))) {
            return invalid(
                StorageItemStatus::ForbiddenItem,
                "item is banned from this storage item",
                static_cast<std::int32_t>(weight),
                exact_weight);
        }

        if (isStorageItemNbt(entry)) {
            if (!rules.allow_nested_storage_items) {
                return invalid(
                    StorageItemStatus::NestedStorageDisabled,
                    "nested storage items are disabled",
                    static_cast<std::int32_t>(weight),
                    exact_weight);
            }
            if (*count != 1) {
                return invalid(
                    StorageItemStatus::InvalidItem,
                    "nested storage items must have a count of one",
                    static_cast<std::int32_t>(weight),
                    exact_weight);
            }
            const auto nested = validateStorageItemImpl(entry, rules, weight_resolver, depth + 1);
            if (!nested.ok()) return nested;
            weight += static_cast<std::int64_t>(nested.used_weight) +
                      rules.nested_storage_item_weight;
            exact_weight = exact_weight && nested.exact_weight;
        }
        else {
            auto unit_weight = embeddedItemWeight(entry);
            if (!unit_weight && weight_resolver) {
                unit_weight = weight_resolver(*nested_identifier, entry);
            }
            if (!unit_weight) {
                if (const auto max_stack = embeddedMaxStackSize(entry)) {
                    unit_weight = storageWeightFromMaxStackSize(*max_stack, rules.max_weight);
                }
            }

            if (!unit_weight) {
                // Unknown items still consume at least one point each. This
                // keeps the lower bound useful without claiming exact weight.
                unit_weight = 1;
                exact_weight = false;
            }
            if (*unit_weight < 1 || *unit_weight > rules.max_weight) {
                return invalid(
                    StorageItemStatus::InvalidItem,
                    "item weight resolver returned an invalid value",
                    static_cast<std::int32_t>(weight),
                    exact_weight);
            }
            weight += static_cast<std::int64_t>(*unit_weight) * *count;
        }

        if (weight > rules.max_weight) {
            return invalid(
                StorageItemStatus::Overweight,
                "storage item exceeds its weight limit",
                static_cast<std::int32_t>(weight),
                exact_weight);
        }
    }

    if (!exact_weight) {
        return {
            StorageItemStatus::WeightUnknown,
            "storage layout is valid, but exact weight requires item-weight information",
            static_cast<std::int32_t>(weight),
            false};
    }
    return {
        StorageItemStatus::Valid,
        "storage item is valid",
        static_cast<std::int32_t>(weight),
        true};
}

inline void validateRules(const StorageItemRules &rules)
{
    if (rules.slot_capacity < 1 || rules.slot_capacity > 64) {
        throw std::invalid_argument("storage item slot capacity must be between 1 and 64");
    }
    if (rules.max_weight < 1 || rules.max_weight > 64) {
        throw std::invalid_argument("storage item maximum weight must be between 1 and 64");
    }
    if (rules.nested_storage_item_weight < 0 ||
        rules.nested_storage_item_weight > rules.max_weight) {
        throw std::invalid_argument("nested storage item weight is outside the supported range");
    }
}

inline std::int32_t entrySlotForSort(const NbtValue &entry) noexcept
{
    const auto *compound = compoundOf(entry);
    if (!compound) return std::numeric_limits<std::int32_t>::max();
    return intField(*compound, {"Slot", "slot"})
        .value_or(std::numeric_limits<std::int32_t>::max());
}

} // namespace storage_item_detail

[[nodiscard]] inline StorageItemValidation validateStorageItem(
    const NbtValue &item,
    const StorageItemRules &rules = {},
    const StorageItemWeightResolver &weight_resolver = {})
{
    try {
        storage_item_detail::validateRules(rules);
    }
    catch (const std::invalid_argument &error) {
        return {
            StorageItemStatus::InvalidContents,
            error.what(),
            0,
            false};
    }
    return storage_item_detail::validateStorageItemImpl(item, rules, weight_resolver, 0);
}

class StorageItemView {
public:
    explicit StorageItemView(
        NbtValue item,
        StorageItemRules rules = {},
        bool create_if_missing = false)
        : item_(std::move(item)), rules_(std::move(rules))
    {
        storage_item_detail::validateRules(rules_);
        if (!storage_item_detail::readItemIdentifier(item_)) {
            throw std::invalid_argument("storage item must be an item compound with an identifier");
        }
        if (!isStorageItemNbt(item_) && !create_if_missing) {
            throw std::invalid_argument("item is not a bundle or serialized storage item");
        }
        (void)mutableContents();
    }

    [[nodiscard]] const NbtValue &item() const noexcept { return item_; }
    [[nodiscard]] NbtValue releaseItem() && noexcept { return std::move(item_); }
    [[nodiscard]] const StorageItemRules &rules() const noexcept { return rules_; }

    [[nodiscard]] std::string itemIdentifier() const
    {
        const auto identifier = storage_item_detail::readItemIdentifier(item_);
        if (!identifier) throw std::logic_error("storage item has no item identifier");
        return *identifier;
    }

    [[nodiscard]] std::vector<StorageItemEntry> contents() const
    {
        const auto *list = storage_item_detail::storageContents(item_);
        if (!list) throw std::logic_error("storage item contents are unavailable");
        std::vector<StorageItemEntry> result;
        result.reserve(list->size());
        for (const auto &entry : *list) {
            const auto *compound = storage_item_detail::compoundOf(entry);
            if (!compound) {
                throw std::invalid_argument("storage item entry must be an NBT compound");
            }
            const auto slot = storage_item_detail::intField(*compound, {"Slot", "slot"});
            if (!slot) throw std::invalid_argument("storage item entry is missing a valid Slot");
            result.push_back({*slot, entry, hashNbt(entry)});
        }
        std::sort(
            result.begin(),
            result.end(),
            [](const auto &left, const auto &right) { return left.slot < right.slot; });
        return result;
    }

    [[nodiscard]] std::optional<StorageItemEntry> getSlot(std::int32_t slot) const
    {
        for (const auto &entry : contents()) {
            if (entry.slot == slot) return entry;
        }
        return std::nullopt;
    }

    [[nodiscard]] StorageItemValidation validate(
        const StorageItemWeightResolver &weight_resolver = {}) const
    {
        return validateStorageItem(item_, rules_, weight_resolver);
    }

    StorageItemView &setSlot(std::int32_t slot, NbtValue item)
    {
        if (slot < 0 || slot >= rules_.slot_capacity) {
            throw std::out_of_range("storage item slot is outside the supported range");
        }
        auto *compound = storage_item_detail::compoundOf(item);
        if (!compound || !storage_item_detail::readItemIdentifier(item) ||
            !storage_item_detail::readItemCount(item)) {
            throw std::invalid_argument("storage item entry must be a valid item compound");
        }
        (*compound)["Slot"] = static_cast<std::int8_t>(slot);

        auto &list = mutableContents();
        list.erase(
            std::remove_if(
                list.begin(),
                list.end(),
                [slot](const NbtValue &entry) {
                    return storage_item_detail::entrySlotForSort(entry) == slot;
                }),
            list.end());
        list.push_back(std::move(item));
        std::sort(
            list.begin(),
            list.end(),
            [](const NbtValue &left, const NbtValue &right) {
                return storage_item_detail::entrySlotForSort(left) <
                       storage_item_detail::entrySlotForSort(right);
            });
        return *this;
    }

    StorageItemView &clearSlot(std::int32_t slot)
    {
        if (slot < 0 || slot >= rules_.slot_capacity) {
            throw std::out_of_range("storage item slot is outside the supported range");
        }
        auto &list = mutableContents();
        list.erase(
            std::remove_if(
                list.begin(),
                list.end(),
                [slot](const NbtValue &entry) {
                    return storage_item_detail::entrySlotForSort(entry) == slot;
                }),
            list.end());
        return *this;
    }

    StorageItemView &replaceContents(std::vector<StorageItemEntry> entries)
    {
        StorageItemView candidate(item_, rules_, true);
        candidate.mutableContents().clear();
        std::set<std::int32_t> occupied;
        for (auto &entry : entries) {
            if (!occupied.insert(entry.slot).second) {
                throw std::invalid_argument("replacement contents contain a duplicate slot");
            }
            candidate.setSlot(entry.slot, std::move(entry.item));
        }
        item_ = std::move(candidate.item_);
        return *this;
    }

private:
    NbtValue item_;
    StorageItemRules rules_;

    NbtList &mutableContents()
    {
        auto *root = storage_item_detail::compoundOf(item_);
        if (!root) throw std::invalid_argument("storage item must be an NBT compound");

        auto tag_it = root->find("tag");
        if (tag_it == root->end()) {
            tag_it = root->emplace("tag", NbtValue::compound({})).first;
        }
        auto *tag = storage_item_detail::compoundOf(tag_it->second);
        if (!tag) throw std::invalid_argument("storage item tag must be an NBT compound");

        auto contents_it = tag->find(std::string(StorageItemContentsKey));
        if (contents_it == tag->end()) {
            contents_it = tag->emplace(
                std::string(StorageItemContentsKey),
                NbtValue::list({})).first;
        }
        auto *contents = storage_item_detail::listOf(contents_it->second);
        if (!contents) {
            throw std::invalid_argument(
                "storage_item_component_content must be an NBT list");
        }
        return *contents;
    }
};

} // namespace endstone_blockdata
