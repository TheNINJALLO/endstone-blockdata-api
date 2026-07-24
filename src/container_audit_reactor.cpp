#include "endstone_blockdata/container_audit_reactor.h"

namespace endstone_blockdata {
std::size_t ContainerAuditReactor::Hash::operator()(const BlockLocation &location) const noexcept {
    std::size_t value = std::hash<std::string>{}(location.dimension);
    auto mix = [&value](int n) {
        value ^= std::hash<int>{}(n) + 0x9e3779b9U + (value << 6U) + (value >> 2U);
    };
    mix(location.x); mix(location.y); mix(location.z);
    return value;
}

bool ContainerAuditReactor::arm(const BlockLocation &location) {
    auto snapshot = service_.capture(location);
    if (!snapshot || !snapshot->block_entity) return false;
    std::scoped_lock lock(mutex_);
    armed_[location] = std::move(*snapshot);
    return true;
}

std::optional<BlockEntityAuditDelta> ContainerAuditReactor::inspect(const BlockLocation &location, bool rearm) {
    BlockSnapshot before;
    {
        std::scoped_lock lock(mutex_);
        auto found = armed_.find(location);
        if (found == armed_.end()) return std::nullopt;
        before = found->second;
    }
    auto after = service_.capture(location);
    if (!after) return std::nullopt;
    auto delta = diffSnapshots(before, *after);
    std::scoped_lock lock(mutex_);
    if (rearm) armed_[location] = std::move(*after);
    else armed_.erase(location);
    return delta;
}

void ContainerAuditReactor::forget(const BlockLocation &location) {
    std::scoped_lock lock(mutex_);
    armed_.erase(location);
}
void ContainerAuditReactor::clear() {
    std::scoped_lock lock(mutex_);
    armed_.clear();
}
std::size_t ContainerAuditReactor::armedCount() const {
    std::scoped_lock lock(mutex_);
    return armed_.size();
}
} // namespace endstone_blockdata
