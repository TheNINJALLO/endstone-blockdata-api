#pragma once
#include "endstone_blockdata/native_adapter.h"
#include <memory>
#include <string_view>

namespace endstone { class Server; }

namespace endstone_blockdata {
// Exact Minecraft Bedrock server/Endstone pair supported by this adapter:
//   BDS 1.26.45 -> Endstone v0.11.10
[[nodiscard]] bool isSupportedBds2645Build(std::string_view build) noexcept;
[[nodiscard]] bool isExpectedBds2645Build(std::string_view runtime_build,
                                          std::string_view packaged_build) noexcept;
[[nodiscard]] bool isExpectedEndstoneVersion(std::string_view runtime_version,
                                             std::string_view packaged_version) noexcept;
[[nodiscard]] std::shared_ptr<IBedrockBlockAdapter> makeBds2645Adapter(endstone::Server &server);
}
