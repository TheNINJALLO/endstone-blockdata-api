#pragma once

class Level;

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

} // namespace endstone_blockdata
