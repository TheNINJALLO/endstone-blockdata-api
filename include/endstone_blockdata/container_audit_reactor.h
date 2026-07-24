#pragma once
#include "endstone_blockdata/audit.h"
#include "endstone_blockdata/block_data_service.h"
#include <mutex>
#include <optional>
#include <unordered_map>

namespace endstone_blockdata {
// Reusable anti-grief primitive. Event listeners call arm() before an action and
// inspect() afterwards. It stores detached snapshots only and is safe to keep
// beyond the lifetime of the live Endstone Block object.
class ContainerAuditReactor {
public:
    explicit ContainerAuditReactor(BlockDataService &service) : service_(service) {}
    [[nodiscard]] bool arm(const BlockLocation &location);
    [[nodiscard]] std::optional<BlockEntityAuditDelta> inspect(const BlockLocation &location,
                                                                bool rearm = true);
    void forget(const BlockLocation &location);
    void clear();
    [[nodiscard]] std::size_t armedCount() const;

private:
    struct Hash {
        std::size_t operator()(const BlockLocation &location) const noexcept;
    };
    BlockDataService &service_;
    mutable std::mutex mutex_;
    std::unordered_map<BlockLocation, BlockSnapshot, Hash> armed_;
};
} // namespace endstone_blockdata
