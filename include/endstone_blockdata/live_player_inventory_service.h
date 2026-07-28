#pragma once

#include "endstone_blockdata/player_inventory.h"

#include <endstone/plugin/service.h>

#include <cstdint>
#include <memory>
#include <string_view>

namespace endstone {
class Player;
}

namespace endstone_blockdata {

inline constexpr std::uint32_t PlayerInventoryServiceAbiVersion = 1;
inline constexpr std::string_view PlayerInventoryServiceName =
    "endstone:player_inventory:v1";

class LivePlayerInventoryService : public endstone::Service {
public:
    ~LivePlayerInventoryService() override = default;
    [[nodiscard]] virtual std::optional<PlayerInventorySnapshot> capture(
        endstone::Player &player) = 0;
    virtual ApplyResult apply(
        endstone::Player &player,
        const PlayerInventoryPatch &patch,
        ConflictPolicy policy = ConflictPolicy::FailIfChanged) = 0;
    [[nodiscard]] virtual std::string adapterName() const = 0;
};

class LivePlayerInventoryServiceProvider final : public LivePlayerInventoryService {
public:
    explicit LivePlayerInventoryServiceProvider(
        std::shared_ptr<PlayerInventoryService> service)
        : service_(std::move(service))
    {
    }

    [[nodiscard]] std::optional<PlayerInventorySnapshot> capture(
        endstone::Player &player) override
    {
        return service_->capture(player);
    }

    ApplyResult apply(
        endstone::Player &player,
        const PlayerInventoryPatch &patch,
        ConflictPolicy policy) override
    {
        return service_->apply(player, patch, policy);
    }

    [[nodiscard]] std::string adapterName() const override
    {
        return service_->adapterName();
    }

private:
    std::shared_ptr<PlayerInventoryService> service_;
};

} // namespace endstone_blockdata
