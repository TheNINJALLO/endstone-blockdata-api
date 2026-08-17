#pragma once
#include "endstone_blockdata/native_adapter.h"
#include <memory>
#include <string_view>

namespace endstone { class Server; }

namespace endstone_blockdata {
// Exact Minecraft Bedrock server/Endstone pair supported by this adapter:
//   BDS 1.26.44 -> Endstone v0.11.9
[[nodiscard]] bool isSupportedBds2644Build(std::string_view build) noexcept;
[[nodiscard]] bool isExpectedBds2644Build(std::string_view runtime_build,
                                          std::string_view packaged_build) noexcept;
[[nodiscard]] bool isExpectedEndstoneVersion(std::string_view runtime_version,
                                             std::string_view packaged_version) noexcept;
[[nodiscard]] std::shared_ptr<IBedrockBlockAdapter> makeBds2644Adapter(endstone::Server &server);
}
