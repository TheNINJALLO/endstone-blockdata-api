#include "endstone_blockdata/block_data_service.h"
#include "endstone_blockdata/bds_26_40_adapter.h"
#include "endstone_blockdata/container.h"
#include "endstone_blockdata/audit.h"
#include "endstone_blockdata/container_audit_reactor.h"
#include <algorithm>
#include <cassert>
#include <iostream>
#include <limits>
using namespace endstone_blockdata;
int main(){
    assert(blockEntityCaptureStatusName(BlockEntityCaptureStatus::NotSupported)=="not_supported");
    assert(blockEntityCaptureStatusName(BlockEntityCaptureStatus::DimensionUnavailable)=="dimension_unavailable");
    assert(blockEntityCaptureStatusName(BlockEntityCaptureStatus::NoActor)=="no_actor");
    assert(blockEntityCaptureStatusName(BlockEntityCaptureStatus::UnsupportedActor)=="unsupported_actor");
    assert(blockEntityCaptureStatusName(BlockEntityCaptureStatus::ComponentMismatch)=="component_mismatch");
    assert(blockEntityCaptureStatusName(BlockEntityCaptureStatus::ContainerUnavailable)=="container_unavailable");
    assert(blockEntityCaptureStatusName(BlockEntityCaptureStatus::Captured)=="captured");
    assert(isSupportedBds2640Build("26.40"));
    assert(isSupportedBds2640Build("1.26.40"));
    assert(isExpectedBds2640Build("26.40", "1.26.40"));
    assert(isExpectedBds2640Build("1.26.40", "26.40"));
    assert(!isSupportedBds2640Build("1.26.32"));
    assert(!isSupportedBds2640Build("26.32"));
    assert(!isSupportedBds2640Build(""));
    assert(!isSupportedBds2640Build("1.26.20"));
    assert(!isSupportedBds2640Build("1.26.34"));
    assert(!isSupportedBds2640Build("server-1.26.40-custom"));
    assert(!isExpectedBds2640Build("26.32", "1.26.40"));
    assert(!isExpectedBds2640Build("26.40", "1.26.32"));
    assert(isExpectedEndstoneVersion("0.11.7", "0.11.7"));
    assert(isExpectedEndstoneVersion("v0.11.7", "0.11.7"));
    assert(isExpectedEndstoneVersion("0.11.7+linux.x86-64", "v0.11.7"));
    assert(isExpectedEndstoneVersion("0.11.7.dev7", "0.11.7"));
    assert(isExpectedEndstoneVersion("v0.11.7.dev7+linux", "v0.11.7"));
    assert(isExpectedEndstoneVersion("0.11.7-dev", "0.11.7"));
    assert(isExpectedEndstoneVersion("0.11.7-dev+linux", "0.11.7"));
    assert(isExpectedEndstoneVersion("0.11.7-dev.snapshot+linux", "0.11.7"));
    assert(!isExpectedEndstoneVersion("0.11.5", "0.11.7"));
    assert(!isExpectedEndstoneVersion("0.11.70", "0.11.7"));
    assert(!isExpectedEndstoneVersion("0.11.7.1", "0.11.7"));
    assert(!isExpectedEndstoneVersion("0.11.7-device", "0.11.7"));
    assert(!isExpectedEndstoneVersion("0.11.7+", "0.11.7"));
    assert(!isExpectedEndstoneVersion("0.11.7.dev", "0.11.7"));
    assert(!isExpectedEndstoneVersion("0.11.7+linux..x64", "0.11.7"));
    assert(!isExpectedEndstoneVersion("0.11.7-dev.snapshot+linux..x64", "0.11.7"));
    std::string nbt_error;
    auto valid_nbt=NbtValue::compound({
      {"bytes",ByteArray{-128,0,127}},
      {"ints",IntArray{std::numeric_limits<std::int32_t>::min(),0,std::numeric_limits<std::int32_t>::max()}},
      {"longs",LongArray{std::numeric_limits<std::int64_t>::min(),0,std::numeric_limits<std::int64_t>::max()}},
      {"list",NbtValue::list({std::int32_t(1),std::int32_t(2)})}});
    assert(validateNbtPayload(valid_nbt,&nbt_error));
    assert(nbt_error.empty());
    auto valid_copy=valid_nbt;
    assert(nbtEqual(valid_nbt,valid_copy));
    const auto valid_root=std::get<NbtValue::CompoundPtr>(valid_copy.value);
    assert(std::holds_alternative<ByteArray>(valid_root->at("bytes").value));
    assert(std::holds_alternative<IntArray>(valid_root->at("ints").value));
    assert(std::holds_alternative<LongArray>(valid_root->at("longs").value));
    assert(!validateNbtPayload(NbtValue::compound({{"invalid",NbtValue{}}}),&nbt_error));
    assert(!validateNbtPayload(NbtValue{NbtValue::ListPtr{}},&nbt_error));
    assert(!validateNbtPayload(NbtValue{NbtValue::CompoundPtr{}},&nbt_error));
    assert(!nbt_error.empty());
    assert(!validateNbtPayload(NbtValue::list({std::int32_t(1),std::string("mixed")}),&nbt_error));
    assert(!validateNbtPayload(NbtValue::list({std::int32_t(1),std::int64_t(2)}),&nbt_error));
    assert(validateNbtPayload(NbtValue::list({true,std::int8_t(1)}),&nbt_error));
    assert(nbt_error.empty());
    BlockDataService svc(makeInMemoryAdapter()); BlockLocation loc{"overworld",10,64,20};
    auto before=svc.capture(loc); assert(before && before->type=="minecraft:air");
    BlockPatch invalid_nbt; invalid_nbt.location=loc; invalid_nbt.nbt_updates["bad"]=NbtValue{};
    assert(svc.apply(invalid_nbt).status==ApplyStatus::InvalidPatch);
    BlockPatch invalid_slot; invalid_slot.location=loc;
    invalid_slot.inventory_updates[-1]={-1,NbtValue::compound({}),0};
    assert(svc.apply(invalid_slot).status==ApplyStatus::InvalidPatch);
    assert(!svc.capture(loc)->block_entity);
    const int edge=std::numeric_limits<int>::max();
    auto edge_region=svc.captureRegion({{"overworld",edge,edge,edge},{"overworld",edge,edge,edge}});
    assert(edge_region.size()==1 && edge_region.front().location.x==edge);
    bool oversized_region_threw=false;
    try { (void)svc.captureRegion({{"overworld",0,0,0},{"overworld",32768,0,0}}); }
    catch(const std::length_error &) { oversized_region_threw=true; }
    assert(oversized_region_threw);
    BlockPatch p; p.location=loc; p.expected_revision=before->revision; p.replacement_type="minecraft:chest";
    p.state_updates["minecraft:cardinal_direction"]=std::string("north"); p.nbt_updates["CustomName"]=std::string("Kingdom Vault");
    p.inventory_updates[0]={0,NbtValue::compound({{"Name",std::string("minecraft:diamond")},{"Count",std::int8_t(4)},
      {"tag",NbtValue::compound({{"display",NbtValue::compound({{"Name",std::string("Protected")}})}})}}),0};
    ContainerAuditReactor reactor(svc);
    // The location is not a block entity yet, so arming must fail cleanly.
    assert(!reactor.arm(loc));
    auto applied=svc.apply(p); assert(applied.ok()); auto after=svc.capture(loc); assert(after && after->block_entity && after->revision!=before->revision);
    assert(after->block_entity_status==BlockEntityCaptureStatus::Captured);
    assert(after->block_entity->is_container && after->block_entity->container_size==1);
    assert(after->block_entity->inventory.size()==1);
    assert(after->block_entity->inventory[0].revision==hashNbt(after->block_entity->inventory[0].item));

    // Snapshot completeness and container metadata are part of its revision.
    BlockSnapshot status_changed=*after;
    status_changed.block_entity_status=BlockEntityCaptureStatus::ContainerUnavailable;
    assert(calculateRevision(status_changed)!=after->revision);
    BlockSnapshot container_flag_changed=*after;
    container_flag_changed.block_entity->is_container=false;
    assert(calculateRevision(container_flag_changed)!=after->revision);
    BlockSnapshot capacity_changed=*after;
    capacity_changed.block_entity->container_size=2;
    assert(calculateRevision(capacity_changed)!=after->revision);

    // Even an empty sparse container changes identity when its known capacity grows.
    BlockLocation empty_capacity_loc{"overworld",11,64,20};
    auto empty_capacity_before=svc.capture(empty_capacity_loc);
    BlockPatch capacity_six_patch; capacity_six_patch.location=empty_capacity_loc;
    capacity_six_patch.expected_revision=empty_capacity_before->revision;
    capacity_six_patch.inventory_removals.insert(5);
    assert(svc.apply(capacity_six_patch).ok());
    auto capacity_six=svc.capture(empty_capacity_loc);
    assert(capacity_six->block_entity && capacity_six->block_entity->inventory.empty());
    assert(capacity_six->block_entity->is_container && capacity_six->block_entity->container_size==6);
    BlockPatch capacity_eleven_patch; capacity_eleven_patch.location=empty_capacity_loc;
    capacity_eleven_patch.expected_revision=capacity_six->revision;
    capacity_eleven_patch.inventory_removals.insert(10);
    assert(svc.apply(capacity_eleven_patch).ok());
    auto capacity_eleven=svc.capture(empty_capacity_loc);
    assert(capacity_eleven->block_entity && capacity_eleven->block_entity->inventory.empty());
    assert(capacity_eleven->block_entity->container_size==11);
    assert(capacity_eleven->revision!=capacity_six->revision);

    // Captures and direct NBT copies must not share mutable compound/list storage.
    auto detached=*after;
    auto detached_root=std::get<NbtValue::CompoundPtr>(detached.block_entity->nbt.value);
    (*detached_root)["CustomName"]=std::string("mutated outside apply");
    auto stored=svc.capture(loc);
    auto stored_root=std::get<NbtValue::CompoundPtr>(stored->block_entity->nbt.value);
    assert(std::get<std::string>((*stored_root)["CustomName"].value)=="Kingdom Vault");

    // Inventory iteration order is not part of a block snapshot's identity.
    BlockSnapshot ordered=*after;
    ordered.block_entity->inventory.push_back({2,NbtValue::compound({{"Name",std::string("minecraft:stone")}}),0});
    BlockSnapshot reversed=ordered;
    std::reverse(reversed.block_entity->inventory.begin(),reversed.block_entity->inventory.end());
    assert(calculateRevision(ordered)==calculateRevision(reversed));

    ContainerView initial_view(*after);
    auto slot_patch=initial_view.patchSlot(0,NbtValue::compound({{"Name",std::string("minecraft:gold_ingot")}}));
    assert(slot_patch.inventory_updates.at(0).revision==after->block_entity->inventory[0].revision);

    BlockSnapshot shelf_snapshot;
    shelf_snapshot.location={"overworld",8,70,8};
    shelf_snapshot.block_entity_status=BlockEntityCaptureStatus::Captured;
    shelf_snapshot.revision=1234;
    shelf_snapshot.block_entity=BlockEntitySnapshot{
        "minecraft:shelf",NbtValue::compound({}),"",true,true,3,
        {{1,NbtValue::compound({{"Name",std::string("minecraft:diamond")},
                                {"Count",std::int8_t(2)}}),77}}};
    ShelfView shelf(shelf_snapshot);
    assert(shelf.kind()==ShelfKind::Shelf && shelf.capacity()==3);
    const auto shelf_slots=shelf.slots();
    assert(!shelf_slots[0] && shelf_slots[1] && !shelf_slots[2]);
    const auto shelf_patch=shelf.patchSlot(
        2,NbtValue::compound({{"Name",std::string("minecraft:emerald")},
                              {"Count",std::int8_t(4)}}));
    assert(shelf_patch.expected_revision==1234 && shelf_patch.inventory_updates.contains(2));
    bool wrong_shelf_count_type=false;
    try {
        (void)shelf.patchSlot(0,NbtValue::compound({
            {"Name",std::string("minecraft:stone")},{"Count",false}}));
    } catch(const std::invalid_argument &) { wrong_shelf_count_type=true; }
    assert(wrong_shelf_count_type);
    const auto shelf_batch=shelf.patchSlots(
        {{0,NbtValue::compound({{"Name",std::string("minecraft:stone")},
                                 {"Count",std::int8_t(1)}})}},{1});
    assert(shelf_batch.inventory_updates.contains(0));
    assert(shelf_batch.inventory_removals.contains(1));
    auto shelf_replacement=shelf.replaceSlots({
        NbtValue::compound({{"Name",std::string("minecraft:diamond")},
                            {"Count",std::int8_t(1)}}),
        std::nullopt,
        NbtValue::compound({{"Name",std::string("minecraft:emerald")},
                            {"Count",std::int8_t(2)}}),
    });
    assert(shelf_replacement.inventory_updates.size()==2);
    assert(shelf_replacement.inventory_removals==std::set<std::int32_t>{1});

    BlockSnapshot chiseled=shelf_snapshot;
    chiseled.block_entity->type="minecraft:chiseled_bookshelf";
    chiseled.block_entity->container_size=6;
    chiseled.block_entity->inventory.clear();
    ShelfView books(chiseled);
    assert(books.kind()==ShelfKind::ChiseledBookshelf && books.capacity()==6);
    (void)books.patchSlot(5,NbtValue::compound({
        {"Name",std::string("minecraft:written_book")},{"Count",std::int8_t(1)}}));
    bool invalid_chiseled=false;
    try {
        (void)books.patchSlot(0,NbtValue::compound({
            {"Name",std::string("minecraft:diamond")},{"Count",std::int8_t(1)}}));
    } catch(const std::invalid_argument &) { invalid_chiseled=true; }
    assert(invalid_chiseled);

    BlockPatch unsupported; unsupported.location=loc; unsupported.replacement_type="minecraft:stone";
    for(auto policy:{ConflictPolicy::MergeChangedPaths,ConflictPolicy::MergeInventorySlots,ConflictPolicy::Replace})
        assert(svc.apply(unsupported,policy).status==ApplyStatus::Unsupported);
    assert(svc.capture(loc)->type==after->type);

    assert(reactor.arm(loc));
    BlockPatch change; change.location=loc; change.inventory_updates[0]={0,NbtValue::compound({{"Name",std::string("minecraft:emerald")},{"Count",std::int8_t(2)}}),0};
    assert(svc.apply(change, ConflictPolicy::Force).ok());
    auto reaction=reactor.inspect(loc); assert(reaction && !reaction->inventory_changes.empty());
    ContainerView c(*after); assert(c.getSlot(0)); auto delta=diffSnapshots(*before,*after); assert(!delta.empty()); assert(delta.inventory_changes.size()==1);
    BlockPatch stale=p; stale.expected_revision=before->revision; assert(svc.apply(stale).status==ApplyStatus::Conflict);
    std::cout<<"blockdata tests passed\n";
}
