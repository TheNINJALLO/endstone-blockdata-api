#pragma once
#include "endstone_blockdata/adapter.h"
#include <memory>
namespace endstone { class Server; }
namespace endstone_blockdata {
// Uses only Endstone's public API. It supports live block types/states today,
// while block-entity NBT remains unavailable until a verified native adapter is installed.
std::shared_ptr<IBlockAdapter> makeEndstonePublicAdapter(endstone::Server &server);
}
