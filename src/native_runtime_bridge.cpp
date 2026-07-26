#include "endstone/core/level/dimension.h"

#include <cstddef>
#include <stdexcept>

#if defined(_WIN32)
#include <Windows.h>
#define ENDSTONE_BLOCKDATA_LOCAL
#elif defined(__linux__)
#include <link.h>
#define ENDSTONE_BLOCKDATA_LOCAL __attribute__((visibility("hidden")))
#else
#define ENDSTONE_BLOCKDATA_LOCAL
#endif

namespace endstone::runtime {

ENDSTONE_BLOCKDATA_LOCAL void *get_executable_base()
{
#if defined(_WIN32)
    static void *base = [] {
        auto *module = GetModuleHandleW(nullptr);
        if (!module) {
            throw std::runtime_error("Unable to locate the Bedrock server executable");
        }
        return static_cast<void *>(module);
    }();
    return base;
#elif defined(__linux__)
    struct MainExecutable {
        void *base{};
        bool found{};
    };

    static void *base = [] {
        MainExecutable executable;
        dl_iterate_phdr(
            [](dl_phdr_info *info, std::size_t, void *data) {
                auto &result = *static_cast<MainExecutable *>(data);
                if (!info->dlpi_name || info->dlpi_name[0] == '\0') {
                    result.base = reinterpret_cast<void *>(info->dlpi_addr);
                    result.found = true;
                    return 1;
                }
                return 0;
            },
            &executable);
        if (!executable.found) {
            throw std::runtime_error("Unable to locate the Bedrock server executable");
        }
        return executable.base;
    }();
    return base;
#else
#error "The exact Bedrock adapter supports only Windows and Linux"
#endif
}

}  // namespace endstone::runtime

namespace endstone::core {

ENDSTONE_BLOCKDATA_LOCAL ::Dimension &EndstoneDimension::getHandle() const
{
    if (!dimension_.isSet()) {
        throw std::runtime_error("Trying to access a dimension that is no longer valid.");
    }
    return *dimension_.unwrap();
}

}  // namespace endstone::core

#undef ENDSTONE_BLOCKDATA_LOCAL
