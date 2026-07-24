#pragma once
#include "endstone_blockdata/native_adapter.h"
#include <memory>
#include <string_view>

namespace endstone { class Server; }

namespace endstone_blockdata {
// Minecraft Bedrock 26.30-family server builds currently supported by Endstone:
//   BDS 1.26.32 -> Endstone v0.11.5
//   BDS 1.26.33 -> Endstone v0.11.6
[[nodiscard]] bool isSupportedBds2630Build(std::string_view build) noexcept;
[[nodiscard]] std::shared_ptr<IBedrockBlockAdapter> makeBds2630Adapter(endstone::Server &server);
}
