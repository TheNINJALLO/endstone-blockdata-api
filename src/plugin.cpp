#include <endstone/endstone.hpp>
#include <endstone/plugin/service_manager.h>
#include <endstone/plugin/service_priority.h>
#include "endstone_blockdata/bds_26_40_adapter.h"
#include "endstone_blockdata/bds_26_40_player_inventory_adapter.h"
#include "endstone_blockdata/block_data_service.h"
#include "endstone_blockdata/endstone_adapter.h"
#include "endstone_blockdata/live_service.h"
#include "endstone_blockdata/live_player_inventory_service.h"
#include "native_item_bridge.h"
#include "version.h"
#include <memory>
#include <string>
#include <string_view>

class BlockDataPlugin : public endstone::Plugin {
public:
    void onEnable() override {
        std::shared_ptr<endstone_blockdata::IBlockAdapter> adapter;
#if ENDSTONE_BLOCKDATA_NATIVE_2640
        std::string_view exact_verification = "runtime-mismatch";
        if (endstone_blockdata::isExpectedBds2640Build(
                getServer().getMinecraftVersion(), ENDSTONE_BLOCKDATA_BDS_BUILD) &&
            endstone_blockdata::isExpectedEndstoneVersion(
                getServer().getVersion(), ENDSTONE_BLOCKDATA_ENDSTONE_VERSION)) {
            exact_verification = endstone_blockdata::nativeStorageItemBridgeStatusName(
                endstone_blockdata::nativeStorageItemBridgeStatus());
        }
        adapter = endstone_blockdata::makeBds2640Adapter(getServer());
        if (!adapter) {
            getLogger().warning(
                "Exact native adapter unavailable; verification={}; runtime BDS={} Endstone={}; expected BDS={} Endstone={}; "
                "falling back to the public Endstone adapter",
                exact_verification, getServer().getMinecraftVersion(), getServer().getVersion(),
                ENDSTONE_BLOCKDATA_BDS_BUILD, ENDSTONE_BLOCKDATA_ENDSTONE_VERSION);
        }
#endif
        if (!adapter) adapter = endstone_blockdata::makeEndstonePublicAdapter(getServer());
        service_ = std::make_shared<endstone_blockdata::BlockDataService>(std::move(adapter));
        provider_ = std::make_shared<endstone_blockdata::LiveBlockDataServiceProvider>(service_);
        getServer().getServiceManager().registerService(
            std::string(endstone_blockdata::BlockDataServiceName), provider_, *this,
            endstone::ServicePriority::Normal);

#if ENDSTONE_BLOCKDATA_NATIVE_2640
        auto player_inventory_adapter =
            endstone_blockdata::makeBds2640PlayerInventoryAdapter(getServer());
        if (player_inventory_adapter) {
            player_inventory_service_ =
                std::make_shared<endstone_blockdata::PlayerInventoryService>(
                    std::move(player_inventory_adapter));
            player_inventory_provider_ = std::make_shared<
                endstone_blockdata::LivePlayerInventoryServiceProvider>(
                    player_inventory_service_);
            getServer().getServiceManager().registerService(
                std::string(endstone_blockdata::PlayerInventoryServiceName),
                player_inventory_provider_, *this,
                endstone::ServicePriority::Normal);
            getLogger().info(
                "service={} adapter={} main=true armor=true offhand=true ender_chest=true storage_item_reads=true storage_item_writes=false",
                endstone_blockdata::PlayerInventoryServiceName,
                player_inventory_service_->adapterName());
        } else {
            getLogger().warning(
                "Exact player inventory adapter unavailable; verification={}; live player item NBT is disabled",
                exact_verification);
        }
#endif

        const auto caps = service_->capabilities();
        getLogger().info("BlockData API {} enabled; adapter={}; BDS={}",
                         ENDSTONE_BLOCKDATA_VERSION, service_->adapterName(), getServer().getMinecraftVersion());
        getLogger().info("service={} states={} writes={} actor_nbt={} actor_nbt_write={} item_nbt={} inventory={} canonical={} raw_hidden_save={}",
                         endstone_blockdata::BlockDataServiceName, caps.block_states, caps.block_writes,
                         caps.block_entity_nbt, caps.block_entity_nbt_write, caps.item_user_nbt,
                         caps.inventory, caps.canonical_actor_nbt, caps.raw_block_entity_nbt);
        if (service_->adapterName() == "bds-26.40-exact-nbt") {
            getLogger().info(
                "live_features storage_item_reads=true storage_item_writes=true shelf_reads=true shelf_writes=true");
        }
    }

    void onDisable() override {
        getServer().getServiceManager().unregisterAll(*this);
        player_inventory_provider_.reset();
        player_inventory_service_.reset();
        provider_.reset();
        service_.reset();
    }

private:
    std::shared_ptr<endstone_blockdata::BlockDataService> service_;
    std::shared_ptr<endstone_blockdata::LiveBlockDataServiceProvider> provider_;
    std::shared_ptr<endstone_blockdata::PlayerInventoryService> player_inventory_service_;
    std::shared_ptr<endstone_blockdata::LivePlayerInventoryServiceProvider>
        player_inventory_provider_;
};

ENDSTONE_PLUGIN("blockdata_api", ENDSTONE_BLOCKDATA_VERSION, BlockDataPlugin) {
    prefix = "BlockDataAPI";
    description = "Live block-state, block-actor and container NBT service for Endstone";
    website = "https://github.com/TheNINJALLO/endstone-blockdata-api";
    authors = {"Ninj-OS contributors"};
}
