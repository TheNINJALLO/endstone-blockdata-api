#pragma once
#include "endstone_blockdata/block_data_service.h"
#include <endstone/plugin/service.h>
#include <memory>
#include <string_view>

namespace endstone_blockdata {
inline constexpr std::string_view BlockDataServiceName = "endstone:blockdata";

// Public Endstone service contract. Native anti-grief and logging plugins can
// load this interface from Server::getServiceManager() without depending on the
// concrete plugin class or the version-specific BDS adapter implementation.
class LiveBlockDataService : public endstone::Service {
public:
    ~LiveBlockDataService() override = default;
    [[nodiscard]] virtual std::optional<BlockSnapshot> capture(const BlockLocation &location) = 0;
    [[nodiscard]] virtual std::vector<BlockSnapshot> captureRegion(const BlockRegion &region) = 0;
    virtual ApplyResult apply(const BlockPatch &patch,
                              ConflictPolicy policy = ConflictPolicy::FailIfChanged) = 0;
    [[nodiscard]] virtual AdapterCapabilities capabilities() const noexcept = 0;
    [[nodiscard]] virtual std::string adapterName() const = 0;
};

class LiveBlockDataServiceProvider final : public LiveBlockDataService {
public:
    explicit LiveBlockDataServiceProvider(std::shared_ptr<BlockDataService> service)
        : service_(std::move(service)) {}

    [[nodiscard]] std::optional<BlockSnapshot> capture(const BlockLocation &location) override {
        return service_->capture(location);
    }
    [[nodiscard]] std::vector<BlockSnapshot> captureRegion(const BlockRegion &region) override {
        return service_->captureRegion(region);
    }
    ApplyResult apply(const BlockPatch &patch, ConflictPolicy policy) override {
        return service_->apply(patch, policy);
    }
    [[nodiscard]] AdapterCapabilities capabilities() const noexcept override {
        return service_->capabilities();
    }
    [[nodiscard]] std::string adapterName() const override { return service_->adapterName(); }

private:
    std::shared_ptr<BlockDataService> service_;
};
} // namespace endstone_blockdata
