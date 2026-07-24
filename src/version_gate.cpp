#include "endstone_blockdata/bds_26_30_adapter.h"

namespace endstone_blockdata {
bool isSupportedBds2630Build(std::string_view build) noexcept {
    if (build.empty()) return true;
    return build.find("26") != std::string_view::npos ||
           build.find("1.26") != std::string_view::npos ||
           build.find("1.2") != std::string_view::npos;
}
}
