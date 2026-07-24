#pragma once
#include "endstone_blockdata/adapter.h"
#include <mutex>

namespace endstone_blockdata {
class BlockDataService {
public:
    explicit BlockDataService(std::shared_ptr<IBlockAdapter> adapter);
    [[nodiscard]] std::optional<BlockSnapshot> capture(const BlockLocation &location);
    [[nodiscard]] std::vector<BlockSnapshot> captureRegion(const BlockRegion &region);
    ApplyResult apply(const BlockPatch &patch, ConflictPolicy policy = ConflictPolicy::FailIfChanged);
    [[nodiscard]] AdapterCapabilities capabilities() const noexcept;
    [[nodiscard]] std::string adapterName() const;
private:
    std::shared_ptr<IBlockAdapter> adapter_;
};

class BlockTransaction {
public:
    explicit BlockTransaction(BlockDataService &service) : service_(service) {}
    void add(BlockPatch patch) { patches_.push_back(std::move(patch)); }
    std::vector<ApplyResult> commit(ConflictPolicy policy = ConflictPolicy::FailIfChanged);
private:
    BlockDataService &service_;
    std::vector<BlockPatch> patches_;
};
}
