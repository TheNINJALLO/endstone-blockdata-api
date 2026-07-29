#pragma once

#include <memory>

class Level;
class ItemStackBase;
class ItemStack;
class Container;

namespace endstone {
class ItemStack;
}

namespace endstone_blockdata {

// ItemStackBase constructors consult ItemRegistryManager. Endstone's runtime
// implementation is private to its own module, so exact item work supplies the
// same live Level registry explicitly for the duration of an apply operation.
class NativeItemRegistryScope final {
public:
    explicit NativeItemRegistryScope(::Level &level) noexcept;
    ~NativeItemRegistryScope() noexcept;

    NativeItemRegistryScope(const NativeItemRegistryScope &) = delete;
    NativeItemRegistryScope &operator=(const NativeItemRegistryScope &) = delete;
    NativeItemRegistryScope(NativeItemRegistryScope &&) = delete;
    NativeItemRegistryScope &operator=(NativeItemRegistryScope &&) = delete;

private:
    ::Level *previous_{};
};

// Exact BDS 1.26.33 storage-item bridge. Bedrock keeps bundle contents in a
// dynamic container rather than ItemStackBase::mUserData. Clone-flatten makes
// those contents serializable without consuming the live container.
[[nodiscard]] bool verifyNativeStorageItemBridge() noexcept;
void flattenNativeStorageItem(::ItemStackBase &item);

// Converts flattened storage_item_component_content back into Bedrock's live
// dynamic-container representation. The transaction owns every manager
// lifetime until it is explicitly transferred to a destination Container.
class NativeStorageItemTransaction final {
public:
    explicit NativeStorageItemTransaction(::Level &level) noexcept;
    ~NativeStorageItemTransaction();

    NativeStorageItemTransaction(const NativeStorageItemTransaction &) = delete;
    NativeStorageItemTransaction &operator=(const NativeStorageItemTransaction &) = delete;
    NativeStorageItemTransaction(NativeStorageItemTransaction &&) = delete;
    NativeStorageItemTransaction &operator=(NativeStorageItemTransaction &&) = delete;

    [[nodiscard]] bool ready() const noexcept;
    [[nodiscard]] bool materialize(::ItemStack &item) noexcept;

    // replace clears stale destination lifetimes and installs the complete
    // transaction set. append is reserved for verified rollback-failure
    // recovery where both requested and restored stacks may remain live.
    [[nodiscard]] bool replaceContainerLifetimes(::Container &container) noexcept;
    [[nodiscard]] bool appendContainerLifetimes(::Container &container) noexcept;
    [[nodiscard]] bool escrowContainerLifetimes(
        ::Container &container,
        const NativeStorageItemTransaction &other) noexcept;

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

[[nodiscard]] bool hasSerializedNativeStorageContents(
    const ::ItemStackBase &item) noexcept;

// Endstone 0.11.6's public ItemStack is backed by its exact native
// EndstoneItemStack implementation. These helpers bridge that pinned layout
// without importing private endstone::core RTTI or implementation symbols.
[[nodiscard]] bool flattenEndstoneStorageItem(endstone::ItemStack &item);

} // namespace endstone_blockdata
