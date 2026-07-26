#include "endstone_blockdata/bds_26_30_adapter.h"

namespace endstone_blockdata {
bool isSupportedBds2630Build(std::string_view build) noexcept {
    return build == "1.26.33";
}

bool isExpectedEndstoneVersion(std::string_view runtime_version,
                               std::string_view packaged_version) noexcept {
    if (runtime_version.starts_with('v')) runtime_version.remove_prefix(1);
    if (packaged_version.starts_with('v')) packaged_version.remove_prefix(1);
    return !runtime_version.empty() && runtime_version == packaged_version;
}
}
