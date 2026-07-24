#include "endstone_blockdata/block_data_service.h"
#include "endstone_blockdata/bds_26_30_adapter.h"
#include "endstone_blockdata/container.h"
#include "endstone_blockdata/audit.h"
#include "endstone_blockdata/container_audit_reactor.h"
#include <cassert>
#include <iostream>
using namespace endstone_blockdata;
int main(){
    assert(isSupportedBds2630Build("1.26.32")); assert(isSupportedBds2630Build("1.26.33")); assert(!isSupportedBds2630Build("1.26.20"));
    BlockDataService svc(makeInMemoryAdapter()); BlockLocation loc{"overworld",10,64,20};
    auto before=svc.capture(loc); assert(before && before->type=="minecraft:air");
    BlockPatch p; p.location=loc; p.expected_revision=before->revision; p.replacement_type="minecraft:chest";
    p.state_updates["minecraft:cardinal_direction"]=std::string("north"); p.nbt_updates["CustomName"]=std::string("Kingdom Vault");
    p.inventory_updates[0]={0,NbtValue::compound({{"Name",std::string("minecraft:diamond")},{"Count",std::int8_t(4)},
      {"tag",NbtValue::compound({{"display",NbtValue::compound({{"Name",std::string("Protected")}})}})}}),0};
    ContainerAuditReactor reactor(svc);
    // The location is not a block entity yet, so arming must fail cleanly.
    assert(!reactor.arm(loc));
    auto applied=svc.apply(p); assert(applied.ok()); auto after=svc.capture(loc); assert(after && after->block_entity && after->revision!=before->revision);
    assert(reactor.arm(loc));
    BlockPatch change; change.location=loc; change.inventory_updates[0]={0,NbtValue::compound({{"Name",std::string("minecraft:emerald")},{"Count",std::int8_t(2)}}),0};
    assert(svc.apply(change, ConflictPolicy::Force).ok());
    auto reaction=reactor.inspect(loc); assert(reaction && !reaction->inventory_changes.empty());
    ContainerView c(*after); assert(c.getSlot(0)); auto delta=diffSnapshots(*before,*after); assert(!delta.empty()); assert(delta.inventory_changes.size()==1);
    BlockPatch stale=p; stale.expected_revision=before->revision; assert(svc.apply(stale).status==ApplyStatus::Conflict);
    std::cout<<"blockdata tests passed\n";
}
