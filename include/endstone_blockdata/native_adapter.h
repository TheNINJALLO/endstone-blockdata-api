#pragma once
#include "endstone_blockdata/adapter.h"

namespace endstone_blockdata {
// Implement one class per verified BDS build. Never reuse an adapter after a BDS update
// unless its signatures and behavior tests pass.
class IBedrockBlockAdapter : public IBlockAdapter {
public:
    virtual bool verifySymbols() noexcept = 0;
    virtual std::string bedrockBuild() const = 0;
    virtual bool markBlockActorDirty(const BlockLocation &) = 0;
    virtual bool sendBlockActorUpdate(const BlockLocation &) = 0;
};
}
