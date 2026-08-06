#pragma once

#include "endstone_blockdata/player_inventory.h"

#include <memory>

namespace endstone {
class Server;
}

namespace endstone_blockdata {

[[nodiscard]] std::shared_ptr<IPlayerInventoryAdapter>
makeBds2640PlayerInventoryAdapter(endstone::Server &server);

} // namespace endstone_blockdata
