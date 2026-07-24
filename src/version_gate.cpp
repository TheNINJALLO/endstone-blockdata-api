#include "endstone_blockdata/bds_26_30_adapter.h"
namespace endstone_blockdata {
bool isSupportedBds2630Build(std::string_view build) noexcept {
    return build == "1.26.32" || build == "1.26.33";
}
}
