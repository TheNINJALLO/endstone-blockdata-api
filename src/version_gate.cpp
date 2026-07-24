#include "endstone_blockdata/bds_26_30_adapter.h"

namespace endstone_blockdata {
bool isSupportedBds2630Build(std::string_view build) noexcept {
    if (build.empty()) return false;
    return build.find("1.26.30") != std::string_view::npos ||
           build.find("1.26.31") != std::string_view::npos ||
           build.find("1.26.32") != std::string_view::npos ||
           build.find("1.26.33") != std::string_view::npos ||
           build.find("26.30") != std::string_view::npos ||
           build.find("26.31") != std::string_view::npos ||
           build.find("26.32") != std::string_view::npos ||
           build.find("26.33") != std::string_view::npos;
}
}
