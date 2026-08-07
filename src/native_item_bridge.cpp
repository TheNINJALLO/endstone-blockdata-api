#include "native_item_bridge.h"

template <typename T>
class WeakRef;

#include "bedrock/gamerefs/weak_ref.h"
#include "bedrock/nbt/compound_tag.h"
#include "bedrock/world/container.h"
#include "bedrock/world/item/item_instance.h"
#include "bedrock/world/item/item_stack.h"
#include "bedrock/world/item/item_stack_base.h"
#include "bedrock/world/item/registry/item_registry_manager.h"
#include "bedrock/world/level/level.h"
#include "endstone/inventory/item_stack.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>

class DynamicContainerTracker;
class DynamicContainerManager;
class IContainerRegistryAccess;
class IContainerRegistryTracker;

namespace endstone::runtime {
void *get_executable_base();
}

namespace {
thread_local Level *active_item_registry_level = nullptr;

// These RVAs and instruction fingerprints are for the official BDS
// 1.26.40.8 executables only. They deliberately stay here instead of in
// Endstone's symbol table so the plugin never imports an unresolved private
// Bedrock symbol.
#if defined(_WIN32)
constexpr std::uintptr_t FlattenStorageItemRva = 0x027C1710;
constexpr std::uintptr_t FlattenStorageItemCoreRva = 0x027C17E0;
constexpr std::size_t StorageContextOffset = 0x76;
constexpr std::size_t StorageCoreCallOffset = 0x83;
constexpr std::array<std::uint8_t, 23> StorageFunctionPrefix{
    0x55, 0x56, 0x57, 0x48, 0x83, 0xEC, 0x40, 0x48,
    0x8D, 0x6C, 0x24, 0x40, 0x48, 0xC7, 0x45, 0xF8,
    0xFE, 0xFF, 0xFF, 0xFF, 0x48, 0x89, 0xCE,
};
constexpr std::uintptr_t CreateTrackerRva = 0x02375020;
constexpr std::uintptr_t TrackStorageItemRva = 0x02372910;
constexpr std::uintptr_t ManagerGiveLifetimeRva = 0x02DF8890;
constexpr std::ptrdiff_t ContainerOwnerOffset = 0x178;
constexpr std::ptrdiff_t TrackerListOffset = 0x28;
constexpr std::array<std::uint8_t, 40> CreateTrackerPrefix{
    0x55, 0x41, 0x56, 0x56, 0x57, 0x53, 0x48, 0x81,
    0xEC, 0x90, 0x00, 0x00, 0x00, 0x48, 0x8D, 0xAC,
    0x24, 0x80, 0x00, 0x00, 0x00, 0x48, 0xC7, 0x45,
    0x08, 0xFE, 0xFF, 0xFF, 0xFF, 0x4C, 0x89, 0x45,
    0xD0, 0x48, 0x89, 0x55, 0xE0, 0x48, 0x89, 0xCE,
};
constexpr std::array<std::uint8_t, 37> TrackStorageItemPrefix{
    0x55, 0x41, 0x57, 0x41, 0x56, 0x41, 0x54, 0x56,
    0x57, 0x53, 0x48, 0x83, 0xEC, 0x40, 0x48, 0x8D,
    0x6C, 0x24, 0x40, 0x48, 0xC7, 0x45, 0xF8, 0xFE,
    0xFF, 0xFF, 0xFF, 0x48, 0x89, 0xD6, 0x49, 0x8B,
    0x40, 0x08, 0x48, 0x85, 0xC0,
};
constexpr std::array<std::uint8_t, 32> ManagerGiveLifetimePrefix{
    0x55, 0x56, 0x57, 0x48, 0x83, 0xEC, 0x40, 0x48,
    0x8D, 0x6C, 0x24, 0x40, 0x48, 0xC7, 0x45, 0xF8,
    0xFE, 0xFF, 0xFF, 0xFF, 0x48, 0x8B, 0x41, 0x18,
    0x48, 0x85, 0xC0, 0x74, 0x5A, 0xF0, 0xFF, 0x40,
};
#elif defined(__linux__)
constexpr std::uintptr_t FlattenStorageItemRva = 0x0B79B2F0;
constexpr std::uintptr_t FlattenStorageItemCoreRva = 0x0B79B390;
constexpr std::size_t StorageContextOffset = 0x5C;
constexpr std::size_t StorageCoreCallOffset = 0x65;
constexpr std::array<std::uint8_t, 7> StorageFunctionPrefix{
    0x41, 0x56, 0x53, 0x50, 0x49, 0x89, 0xFE,
};
constexpr std::uintptr_t CreateTrackerRva = 0x0B307D90;
constexpr std::uintptr_t TrackStorageItemRva = 0x0B306510;
constexpr std::uintptr_t ReceiveContainerLifetimesRva = 0x0ADCFB40;
constexpr std::uintptr_t ManagerGiveLifetimeRva = 0x0B2E1F50;
constexpr std::ptrdiff_t ContainerOwnerOffset = 0x120;
constexpr std::ptrdiff_t TrackerListOffset = 0x30;
constexpr std::array<std::uint8_t, 29> CreateTrackerPrefix{
    0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54,
    0x53, 0x48, 0x83, 0xEC, 0x10, 0x49, 0x89, 0xD4,
    0x49, 0x89, 0xF5, 0x48, 0x89, 0xFB, 0x48, 0x8B,
    0x05, 0x5B, 0x8E, 0x54, 0x03,
};
constexpr std::array<std::uint8_t, 30> TrackStorageItemPrefix{
    0x55, 0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41,
    0x54, 0x53, 0x50, 0x48, 0x89, 0xFB, 0x48, 0x8B,
    0x42, 0x08, 0x48, 0x85, 0xC0, 0x0F, 0x84, 0xC1,
    0x00, 0x00, 0x00, 0x48, 0x8B, 0x38,
};
constexpr std::array<std::uint8_t, 32> ReceiveContainerLifetimesPrefix{
    0x41, 0x57, 0x41, 0x56, 0x41, 0x55, 0x41, 0x54,
    0x53, 0x49, 0x89, 0xF6, 0x48, 0x89, 0xFB, 0x4C,
    0x8B, 0xA7, 0x20, 0x01, 0x00, 0x00, 0x4C, 0x8B,
    0xAF, 0x28, 0x01, 0x00, 0x00, 0x4D, 0x39, 0xEC,
};
constexpr std::array<std::uint8_t, 36> ManagerGiveLifetimePrefix{
    0x53, 0x48, 0x83, 0xEC, 0x20, 0x48, 0x89, 0xF3,
    0x48, 0x8B, 0x4F, 0x10, 0x48, 0x89, 0x4C, 0x24,
    0x10, 0x48, 0x8B, 0x57, 0x18, 0x48, 0x89, 0x54,
    0x24, 0x18, 0x48, 0x85, 0xD2, 0x74, 0x31, 0xF0,
    0x48, 0xFF, 0x42, 0x08,
};
#else
#error "The exact storage-item bridge supports only Windows and Linux"
#endif

const std::byte *executableBytes()
{
    return static_cast<const std::byte *>(
        endstone::runtime::get_executable_base());
}

bool bytesEqual(const std::byte *actual, const std::uint8_t *expected,
                std::size_t count) noexcept
{
    return std::memcmp(actual, expected, count) == 0;
}

template <std::size_t Size>
bool verifyFunctionPrefix(
    std::uintptr_t function_rva,
    const std::array<std::uint8_t, Size> &prefix) noexcept
{
    return bytesEqual(
        executableBytes() + function_rva, prefix.data(), prefix.size());
}

template <typename Function>
Function executableFunction(std::uintptr_t function_rva) noexcept
{
    const auto address = reinterpret_cast<std::uintptr_t>(executableBytes()) +
                         function_rva;
    return reinterpret_cast<Function>(address);
}

bool verifyStorageFunction(std::uintptr_t function_rva,
                           std::uint8_t context_kind) noexcept
{
    const auto *function = executableBytes() + function_rva;
    if (!bytesEqual(function, StorageFunctionPrefix.data(),
                    StorageFunctionPrefix.size())) {
        return false;
    }

#if defined(_WIN32)
    const std::array<std::uint8_t, 10> context_and_arguments{
        0xC6, 0x07, context_kind, 0x48, 0x89,
        0xF1, 0x48, 0x89, 0xFA, 0x48,
    };
#else
    const std::array<std::uint8_t, 10> context_and_arguments{
        0xC6, 0x03, context_kind, 0x4C, 0x89,
        0xF7, 0x48, 0x89, 0xDE, 0xE8,
    };
#endif
    if (!bytesEqual(function + StorageContextOffset,
                    context_and_arguments.data(),
                    context_and_arguments.size())) {
        return false;
    }

#if defined(_WIN32)
    constexpr std::array<std::uint8_t, 5> before_call{
        0x89, 0x7D, 0xF0, 0xE8, 0x00,
    };
    if (!bytesEqual(function + StorageContextOffset + 10,
                    before_call.data(), before_call.size() - 1)) {
        return false;
    }
#endif

    const auto *call = function + StorageCoreCallOffset;
    if (std::to_integer<std::uint8_t>(*call) != 0xE8) return false;
    std::int32_t displacement{};
    std::memcpy(&displacement, call + 1, sizeof(displacement));
    const auto *target = call + 5 + displacement;
    return target == executableBytes() + FlattenStorageItemCoreRva;
}

using StorageItemFunction = void (*)(::ItemStackBase &);

void invokeStorageFunction(std::uintptr_t function_rva,
                           ::ItemStackBase &item)
{
    executableFunction<StorageItemFunction>(function_rva)(item);
}

template <typename T>
const std::shared_ptr<T> &stackResultSharedPtr(
    const StackRefResult<T> &result) noexcept
{
    static_assert(sizeof(StackRefResult<T>) == sizeof(std::shared_ptr<T>));
    static_assert(alignof(StackRefResult<T>) == alignof(std::shared_ptr<T>));
    return *std::launder(
        reinterpret_cast<const std::shared_ptr<T> *>(std::addressof(result)));
}

template <typename T>
class ConstructibleWeakRef final : public WeakRef<T> {
public:
    explicit ConstructibleWeakRef(const std::weak_ptr<T> &handle)
        : WeakRef<T>(handle)
    {
    }
};

template <typename T>
WeakRef<T> makeExactWeakRef(const std::shared_ptr<T> &shared)
{
    return ConstructibleWeakRef<T>(std::weak_ptr<T>(shared));
}

using CreateTrackerFunction = std::shared_ptr<DynamicContainerTracker> (*)(
    WeakRef<IContainerRegistryAccess>, WeakRef<IContainerRegistryTracker>);
using TrackStorageItemFunction = std::optional<::ItemStack> (*)(
    DynamicContainerTracker *, const ::ItemStack &);
using ManagerGiveLifetimeFunction = void (*)(
    DynamicContainerManager *, ::ContainerOwner *);
#if defined(__linux__)
using ReceiveContainerLifetimesFunction = void (*)(
    ::Container *, const DynamicContainerTracker *);
#endif

std::shared_ptr<DynamicContainerTracker> createStorageTracker(::Level &level)
{
    auto access_result_holder = level.getContainerRegistryAccess();
    auto tracker_result_holder = level.getContainerRegistryTracker();
    const auto &access_result = access_result_holder.get();
    const auto &tracker_result = tracker_result_holder.get();
    const auto access = stackResultSharedPtr(access_result);
    const auto tracker = stackResultSharedPtr(tracker_result);
    if (!access || !tracker) return {};
    return executableFunction<CreateTrackerFunction>(CreateTrackerRva)(
        makeExactWeakRef(access), makeExactWeakRef(tracker));
}

std::optional<std::int64_t> nativeInteger(const ::Tag &tag) noexcept
{
    switch (tag.getId()) {
    case Tag::Type::Byte:
        return static_cast<const ByteTag &>(tag).data;
    case Tag::Type::Short:
        return static_cast<const ShortTag &>(tag).data;
    case Tag::Type::Int:
        return static_cast<const IntTag &>(tag).data;
    case Tag::Type::Int64:
        return static_cast<const Int64Tag &>(tag).data;
    default:
        return std::nullopt;
    }
}

enum class SavedIntegerWidth { Byte, Short };

bool canonicalizeSavedInteger(
    ::CompoundTag &item,
    std::string_view canonical_name,
    std::initializer_list<std::string_view> aliases,
    SavedIntegerWidth width,
    std::int64_t minimum,
    std::int64_t maximum,
    bool required,
    std::int64_t default_value = 0)
{
    ::Tag *source = item.get(canonical_name);
    std::string_view source_name = canonical_name;
    if (!source) {
        for (const auto alias : aliases) {
            if ((source = item.get(alias))) {
                source_name = alias;
                break;
            }
        }
    }
    const auto value = source ? nativeInteger(*source)
                              : std::optional<std::int64_t>(default_value);
    if ((required && !source) || !value || *value < minimum || *value > maximum)
        return false;

    if (width == SavedIntegerWidth::Byte) {
        item.putByte(std::string(canonical_name),
                     static_cast<std::uint8_t>(*value));
    }
    else {
        item.putShort(std::string(canonical_name),
                      static_cast<std::int16_t>(*value));
    }
    if (source && source_name != canonical_name) item.remove(source_name);
    return true;
}

bool canonicalizeSavedStorageList(::ListTag &contents, std::size_t depth);

bool canonicalizeSavedItem(::CompoundTag &item, std::size_t depth)
{
    if (depth > 64) return false;

    auto *name_tag = item.get("Name");
    auto *name = name_tag && name_tag->getId() == Tag::Type::String
                     ? static_cast<StringTag *>(name_tag)
                     : nullptr;
    std::string_view name_source = "Name";
    if (!name) {
        for (const auto alias : {std::string_view("name"), std::string_view("id")}) {
            auto *alias_tag = item.get(alias);
            if (alias_tag && alias_tag->getId() == Tag::Type::String) {
                name = static_cast<StringTag *>(alias_tag);
                name_source = alias;
                break;
            }
        }
    }
    if (!name || name->data.empty()) return false;
    if (name_source != "Name") {
        item.putString("Name", name->data);
        item.remove(name_source);
    }

    if (!canonicalizeSavedInteger(
            item, "Slot", {"slot"}, SavedIntegerWidth::Byte,
            0, 255, true) ||
        !canonicalizeSavedInteger(
            item, "Count", {"count"}, SavedIntegerWidth::Byte,
            1, 255, false, 1) ||
        !canonicalizeSavedInteger(
            item, "Damage", {"damage"}, SavedIntegerWidth::Short,
            std::numeric_limits<std::int16_t>::min(),
            std::numeric_limits<std::int16_t>::max(), false) ||
        !canonicalizeSavedInteger(
            item, "Aux", {"aux"}, SavedIntegerWidth::Short,
            std::numeric_limits<std::int16_t>::min(),
            std::numeric_limits<std::int16_t>::max(), false) ||
        !canonicalizeSavedInteger(
            item, "LegacyId", {"legacy_id"}, SavedIntegerWidth::Short,
            std::numeric_limits<std::int16_t>::min(),
            std::numeric_limits<std::int16_t>::max(), false)) {
        return false;
    }

    auto *user_data = item.getCompound("tag");
    if (!user_data) {
        if (const auto *alias = item.getCompound("user_data")) {
            item.putCompound("tag", alias->clone());
            item.remove("user_data");
            user_data = item.getCompound("tag");
        }
    }
    if (user_data) {
        if (auto *nested = user_data->getList(
                "storage_item_component_content")) {
            return canonicalizeSavedStorageList(*nested, depth + 1);
        }
    }
    return true;
}

bool canonicalizeSavedStorageList(::ListTag &contents, std::size_t depth)
{
    if (depth > 64) return false;
    for (std::size_t index = 0; index < contents.size(); ++index) {
        auto *entry = contents.getCompound(static_cast<int>(index));
        if (!entry || !canonicalizeSavedItem(*entry, depth)) return false;
    }
    return true;
}

bool canonicalizeNativeStorageContents(::ItemStackBase &item) noexcept
{
    try {
        auto *user_data = item.getUserData();
        if (!user_data) return true;
        auto *contents = user_data->getList("storage_item_component_content");
        return !contents || canonicalizeSavedStorageList(*contents, 0);
    }
    catch (...) {
        return false;
    }
}

bool validContainerOwnerStorage(const std::byte *storage) noexcept
{
    constexpr std::size_t MaxOwnedContainerLifetimes = 65536;
    std::array<std::uintptr_t, 3> vector_state{};
    std::memcpy(vector_state.data(), storage, sizeof(vector_state));

    const auto begin = vector_state[0];
    const auto end = vector_state[1];
    const auto capacity = vector_state[2];
    if (begin == 0) return end == 0 && capacity == 0;
    if (end == 0 || capacity == 0 || begin > end || end > capacity)
        return false;
    if (begin % alignof(::ContainerOwner::OwnedContainer) != 0)
        return false;

    const auto used_bytes = end - begin;
    const auto capacity_bytes = capacity - begin;
    constexpr auto element_size = sizeof(::ContainerOwner::OwnedContainer);
    if (used_bytes % element_size != 0 ||
        capacity_bytes % element_size != 0) {
        return false;
    }
    return used_bytes / element_size <= MaxOwnedContainerLifetimes &&
           capacity_bytes / element_size <= MaxOwnedContainerLifetimes;
}

::ContainerOwner *containerOwner(::Container &container) noexcept
{
    static_assert(sizeof(::ContainerOwner) == 24);
    auto *storage = reinterpret_cast<std::byte *>(std::addressof(container)) +
                    ContainerOwnerOffset;
    if (reinterpret_cast<std::uintptr_t>(storage) % alignof(::ContainerOwner) !=
            0 ||
        !validContainerOwnerStorage(storage)) {
        return nullptr;
    }
    return std::launder(reinterpret_cast<::ContainerOwner *>(storage));
}

void *readPointer(const void *address) noexcept
{
    void *value = nullptr;
    std::memcpy(&value, address, sizeof(value));
    return value;
}

std::optional<std::vector<DynamicContainerManager *>> trackerManagers(
    const DynamicContainerTracker &tracker)
{
    constexpr std::size_t MaxTrackedManagers = 65536;
    std::vector<DynamicContainerManager *> managers;
    const auto *storage = reinterpret_cast<const std::byte *>(
        std::addressof(tracker));
#if defined(_WIN32)
    void *sentinel = readPointer(storage + TrackerListOffset);
    if (!sentinel) return std::nullopt;
    void *node = readPointer(sentinel);
    while (node != sentinel) {
        if (!node || managers.size() >= MaxTrackedManagers)
            return std::nullopt;
        auto *manager = static_cast<DynamicContainerManager *>(
            readPointer(static_cast<const std::byte *>(node) + 0x20));
        if (!manager) return std::nullopt;
        managers.push_back(manager);
        node = readPointer(node);
    }
#else
    void *node = readPointer(storage + TrackerListOffset);
    while (node) {
        if (managers.size() >= MaxTrackedManagers) return std::nullopt;
        auto *manager = static_cast<DynamicContainerManager *>(
            readPointer(static_cast<const std::byte *>(node) + 0x20));
        if (!manager) return std::nullopt;
        managers.push_back(manager);
        node = readPointer(node);
    }
#endif
    return managers;
}

bool appendManagers(
    const std::vector<DynamicContainerManager *> &managers,
    ::ContainerOwner &owner) noexcept
{
    auto &lifetimes = owner.owned_containers;
    const auto original_size = lifetimes.size();
    try {
        if (managers.size() > lifetimes.max_size() - original_size)
            return false;
        lifetimes.reserve(original_size + managers.size());
        const auto give = executableFunction<ManagerGiveLifetimeFunction>(
            ManagerGiveLifetimeRva);
        for (auto *manager : managers) {
            const auto before = lifetimes.size();
            give(manager, std::addressof(owner));
            if (lifetimes.size() != before + 1) {
                lifetimes.erase(
                    lifetimes.begin() +
                        static_cast<std::ptrdiff_t>(original_size),
                    lifetimes.end());
                return false;
            }
        }
        return true;
    }
    catch (...) {
        if (lifetimes.size() >= original_size) {
            lifetimes.erase(
                lifetimes.begin() +
                    static_cast<std::ptrdiff_t>(original_size),
                lifetimes.end());
        }
        return false;
    }
}

bool replaceManagers(
    const std::vector<DynamicContainerManager *> &managers,
    ::ContainerOwner &owner) noexcept
{
    auto &lifetimes = owner.owned_containers;
    const auto original_size = lifetimes.size();
    if (!appendManagers(managers, owner)) return false;

    // Appending before erasing gives this operation a strong lifetime
    // guarantee: every old manager remains owned until the complete new set
    // has been installed. OwnedContainer is a shared_ptr-sized handle, so
    // erasing the committed prefix cannot allocate or throw.
    static_assert(std::is_nothrow_move_assignable_v<
                  ::ContainerOwner::OwnedContainer>);
    lifetimes.erase(
        lifetimes.begin(),
        lifetimes.begin() + static_cast<std::ptrdiff_t>(original_size));
    return true;
}

::ItemInstance *endstoneNativeItem(endstone::ItemStack &item) noexcept
{
    // Endstone 0.11.8 ItemStack contains exactly one unique_ptr<Impl>. Its
    // concrete EndstoneItemStack begins with the Impl vptr and then stores an
    // ItemInstance. This is an intentionally pinned x64 layout bridge; using
    // private Endstone RTTI here previously made the plugin fail to load.
    static_assert(sizeof(endstone::ItemStack) == sizeof(void *));
    static_assert(sizeof(::ItemInstance) == sizeof(::ItemStackBase));

    void *implementation = nullptr;
    std::memcpy(&implementation, &item, sizeof(implementation));
    if (!implementation) return nullptr;
    auto *storage = static_cast<std::byte *>(implementation) + sizeof(void *);
    return std::launder(reinterpret_cast<::ItemInstance *>(storage));
}
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

NativeStorageItemBridgeStatus nativeStorageItemBridgeStatus() noexcept
{
    try {
        if (sizeof(void *) != 8) {
            return NativeStorageItemBridgeStatus::UnsupportedPointerWidth;
        }
        if (!executableBytes()) {
            return NativeStorageItemBridgeStatus::ExecutableBaseUnavailable;
        }
        if (!verifyStorageFunction(FlattenStorageItemRva, 2)) {
            return NativeStorageItemBridgeStatus::FlattenStorageItemMismatch;
        }
        if (!verifyFunctionPrefix(CreateTrackerRva, CreateTrackerPrefix)) {
            return NativeStorageItemBridgeStatus::CreateTrackerMismatch;
        }
        if (!verifyFunctionPrefix(TrackStorageItemRva, TrackStorageItemPrefix)) {
            return NativeStorageItemBridgeStatus::TrackStorageItemMismatch;
        }
        if (!verifyFunctionPrefix(
                ManagerGiveLifetimeRva, ManagerGiveLifetimePrefix)) {
            return NativeStorageItemBridgeStatus::ManagerGiveLifetimeMismatch;
        }
#if defined(__linux__)
        if (!verifyFunctionPrefix(
                ReceiveContainerLifetimesRva,
                ReceiveContainerLifetimesPrefix)) {
            return NativeStorageItemBridgeStatus::ReceiveContainerLifetimesMismatch;
        }
#endif
        return NativeStorageItemBridgeStatus::Ready;
    }
    catch (...) {
        return NativeStorageItemBridgeStatus::VerificationError;
    }
}

std::string_view nativeStorageItemBridgeStatusName(
    NativeStorageItemBridgeStatus status) noexcept
{
    switch (status) {
    case NativeStorageItemBridgeStatus::Ready: return "ready";
    case NativeStorageItemBridgeStatus::UnsupportedPointerWidth:
        return "unsupported-pointer-width";
    case NativeStorageItemBridgeStatus::ExecutableBaseUnavailable:
        return "executable-base-unavailable";
    case NativeStorageItemBridgeStatus::FlattenStorageItemMismatch:
        return "flatten-storage-item-mismatch";
    case NativeStorageItemBridgeStatus::CreateTrackerMismatch:
        return "create-tracker-mismatch";
    case NativeStorageItemBridgeStatus::TrackStorageItemMismatch:
        return "track-storage-item-mismatch";
    case NativeStorageItemBridgeStatus::ManagerGiveLifetimeMismatch:
        return "manager-give-lifetime-mismatch";
    case NativeStorageItemBridgeStatus::ReceiveContainerLifetimesMismatch:
        return "receive-container-lifetimes-mismatch";
    case NativeStorageItemBridgeStatus::VerificationError:
        return "verification-error";
    }
    return "unknown";
}

bool verifyNativeStorageItemBridge() noexcept
{
    return nativeStorageItemBridgeStatus() ==
           NativeStorageItemBridgeStatus::Ready;
}

void flattenNativeStorageItem(ItemStackBase &item)
{
    if (!verifyNativeStorageItemBridge()) {
        throw std::runtime_error(
            "BDS 1.26.40 storage-item fingerprint verification failed");
    }
    invokeStorageFunction(FlattenStorageItemRva, item);
}

class NativeStorageItemTransaction::Impl final {
public:
    explicit Impl(::Level &level) : tracker(createStorageTracker(level)) {}

    std::shared_ptr<DynamicContainerTracker> tracker;
};

NativeStorageItemTransaction::NativeStorageItemTransaction(
    ::Level &level) noexcept
{
    try {
        if (verifyNativeStorageItemBridge()) {
            impl_ = std::make_unique<Impl>(level);
        }
    }
    catch (...) {
        impl_.reset();
    }
}

NativeStorageItemTransaction::~NativeStorageItemTransaction() = default;

bool NativeStorageItemTransaction::ready() const noexcept
{
    return impl_ && static_cast<bool>(impl_->tracker);
}

bool NativeStorageItemTransaction::materialize(::ItemStack &item) noexcept
{
    try {
        if (!ready()) return false;
        if (!hasSerializedNativeStorageContents(item)) return true;
        if (!canonicalizeNativeStorageContents(item)) return false;

        auto tracked = executableFunction<TrackStorageItemFunction>(
            TrackStorageItemRva)(impl_->tracker.get(), item);
        if (!tracked) return false;
        item.setNull(std::nullopt);
        item = *tracked;
        return true;
    }
    catch (...) {
        return false;
    }
}

bool NativeStorageItemTransaction::replaceContainerLifetimes(
    ::Container &container) noexcept
{
    try {
        if (!ready()) return false;
        const auto managers = trackerManagers(*impl_->tracker);
        if (!managers) return false;
        auto *owner = containerOwner(container);
        return owner && replaceManagers(*managers, *owner);
    }
    catch (...) {
        return false;
    }
}

bool NativeStorageItemTransaction::appendContainerLifetimes(
    ::Container &container) noexcept
{
    try {
        if (!ready()) return false;
        const auto managers = trackerManagers(*impl_->tracker);
        if (!managers) return false;
        auto *owner = containerOwner(container);
        return owner && appendManagers(*managers, *owner);
    }
    catch (...) {
        return false;
    }
}

bool NativeStorageItemTransaction::escrowContainerLifetimes(
    ::Container &container,
    const NativeStorageItemTransaction &other) noexcept
{
    try {
        if (!ready() || !other.ready()) return false;
        const auto own_managers = trackerManagers(*impl_->tracker);
        const auto other_managers = trackerManagers(*other.impl_->tracker);
        if (!own_managers || !other_managers) return false;

        std::vector<DynamicContainerManager *> combined;
        combined.reserve(own_managers->size() + other_managers->size());
        combined.insert(
            combined.end(), own_managers->begin(), own_managers->end());
        combined.insert(
            combined.end(), other_managers->begin(), other_managers->end());
        auto *owner = containerOwner(container);
        return owner && appendManagers(combined, *owner);
    }
    catch (...) {
        return false;
    }
}

bool hasSerializedNativeStorageContents(
    const ::ItemStackBase &item) noexcept
{
    try {
        const auto *user_data = item.getUserData();
        return user_data &&
               user_data->getList("storage_item_component_content") != nullptr;
    }
    catch (...) {
        return false;
    }
}

bool flattenEndstoneStorageItem(endstone::ItemStack &item)
{
    try {
        auto *native = endstoneNativeItem(item);
        if (!native) return false;
        flattenNativeStorageItem(*native);
        return true;
    }
    catch (...) {
        return false;
    }
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
