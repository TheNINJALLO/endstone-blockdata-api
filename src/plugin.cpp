#include <format>
#ifndef format_context
#define format_context std::format_context
#endif

#include <endstone/endstone.hpp>
#include <endstone/plugin/service_manager.h>
#include <endstone/plugin/service_priority.h>
#include "endstone_blockdata/bds_26_30_adapter.h"
#include "endstone_blockdata/block_data_service.h"
#include "endstone_blockdata/endstone_adapter.h"
#include "endstone_blockdata/live_service.h"
#include "version.h"
#include <memory>
#include <string>

class BlockDataPlugin : public endstone::Plugin {
public:
    void onEnable() override {
        std::shared_ptr<endstone_blockdata::IBlockAdapter> adapter;
#if ENDSTONE_BLOCKDATA_NATIVE_2630
        adapter = endstone_blockdata::makeBds2630Adapter(getServer());
#endif
        if (!adapter) adapter = endstone_blockdata::makeEndstonePublicAdapter(getServer());
        service_ = std::make_shared<endstone_blockdata::BlockDataService>(std::move(adapter));
        provider_ = std::make_shared<endstone_blockdata::LiveBlockDataServiceProvider>(service_);
        getServer().getServiceManager().registerService(
            std::string(endstone_blockdata::BlockDataServiceName), provider_, *this,
            endstone::ServicePriority::Normal);

        const auto caps = service_->capabilities();
        getLogger().info("BlockData API {} enabled; adapter={}; BDS={}",
                         ENDSTONE_BLOCKDATA_VERSION, service_->adapterName(), getServer().getMinecraftVersion());
        getLogger().info("service={} states={} writes={} actor_nbt={} actor_nbt_write={} item_nbt={} inventory={} canonical={} raw_hidden_save={}",
                         endstone_blockdata::BlockDataServiceName, caps.block_states, caps.block_writes,
                         caps.block_entity_nbt, caps.block_entity_nbt_write, caps.item_user_nbt,
                         caps.inventory, caps.canonical_actor_nbt, caps.raw_block_entity_nbt);
    }

    void onDisable() override {
        getServer().getServiceManager().unregisterAll(*this);
        provider_.reset();
        service_.reset();
    }

private:
    std::shared_ptr<endstone_blockdata::BlockDataService> service_;
    std::shared_ptr<endstone_blockdata::LiveBlockDataServiceProvider> provider_;
};

ENDSTONE_PLUGIN("endstone_blockdata", ENDSTONE_BLOCKDATA_VERSION, BlockDataPlugin) {
    prefix = "BlockData";
    description = "Live block-state, block-actor and container NBT service for Endstone";
    website = "https://github.com/TheNINJALLO/endstone-blockdata-api";
    authors = {"Ninj-OS contributors"};
}
