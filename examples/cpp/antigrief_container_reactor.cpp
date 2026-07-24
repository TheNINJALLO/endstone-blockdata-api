// Minimal native consumer example. This is intended to live inside another
// Endstone C++ plugin, where `server` is the plugin's Server reference.
#include <endstone/endstone.hpp>
#include "endstone_blockdata/audit.h"
#include "endstone_blockdata/live_service.h"
#include <optional>

using namespace endstone_blockdata;

class ContainerReactor {
public:
    explicit ContainerReactor(endstone::Server &server)
        : api_(server.getServiceManager().load<LiveBlockDataService>(
              std::string(BlockDataServiceName))) {}

    [[nodiscard]] bool ready() const {
        return api_ && api_->capabilities().block_entity_nbt && api_->capabilities().inventory;
    }

    void remember(const BlockLocation &location) {
        if (api_) before_ = api_->capture(location);
    }

    [[nodiscard]] std::optional<BlockEntityAuditDelta> inspect(const BlockLocation &location) {
        if (!api_ || !before_) return std::nullopt;
        auto after = api_->capture(location);
        if (!after) return std::nullopt;
        auto delta = diffSnapshots(*before_, *after);
        before_ = std::move(after);
        return delta;
    }

private:
    std::shared_ptr<LiveBlockDataService> api_;
    std::optional<BlockSnapshot> before_;
};
