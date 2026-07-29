import sys, unittest
sys.path.insert(0,"python")
sys.path.insert(0,"examples/python")
from endstone_blockdata import *
from shelf_shop import ShelfListing, ShelfShop, StockReservation

class FalseyInMemoryAdapter(InMemoryAdapter):
    def __bool__(self): return False

class FakeLiveBridge:
    def __init__(self):
        self.applied=None
        self.capture_calls=[]
        self.capture_region_calls=[]
    def __bool__(self): return False
    def available(self,server): return True
    def capabilities(self,server): return {"adapter":"exact","inventory":True}
    def _snapshot(self,dimension,x,y,z):
        return {
            "location":{"dimension":dimension,"x":x,"y":y,"z":z},
            "type":"minecraft:shelf","runtime_id":7,"states":{},"revision":91,
            "block_entity_status":"captured",
            "block_entity":{
                "type":"minecraft:shelf","nbt":{"id":"minecraft:shelf"},
                "snbt":"{}","canonical":True,"is_container":True,
                "container_size":3,
                "inventory":[{"slot":0,"item":{"Name":"minecraft:diamond","Count":2},"revision":8}],
            },
        }
    def capture(self,server,dimension,x,y,z):
        self.capture_calls.append((dimension,x,y,z))
        return self._snapshot(dimension,x,y,z)
    def capture_region(self,server,dimension,min_x,min_y,min_z,max_x,max_y,max_z):
        self.capture_region_calls.append(
            (dimension,min_x,min_y,min_z,max_x,max_y,max_z)
        )
        return [
            self._snapshot(dimension,min_x,min_y,min_z),
            self._snapshot(dimension,max_x,max_y,max_z),
        ]
    def apply(self,server,patch,policy):
        self.applied=(patch,policy)
        return {"ok":True,"status":"applied","message":"done","resulting_revision":92}

class TestBlockData(unittest.TestCase):
    def test_patch_conflict_and_audit(self):
        svc=BlockDataService(); before=svc.capture("overworld",(1,64,2))
        p=BlockPatch(before.location,before.revision,"minecraft:chest",nbt_updates={"CustomName":"Vault"},inventory_updates={0:{"Name":"minecraft:diamond","Count":4,"tag":{"display":{"Name":"Protected"}}}})
        self.assertTrue(svc.apply(p).ok)
        after=svc.capture("overworld",(1,64,2)); view=ContainerView(after)
        self.assertEqual(view.get_item(0)["Count"],4)
        self.assertEqual(after.block_entity_status,"captured")
        self.assertTrue(after.block_entity.is_container)
        self.assertEqual(view.capacity,1)
        self.assertEqual(view.occupied_slots,1)
        delta=svc.diff(before,after); self.assertEqual(delta.inventory_changes[0].kind,InventoryChangeKind.ADDED)
        self.assertFalse(svc.apply(p).ok)
    def test_revision_is_independent_of_inventory_storage_order(self):
        loc=BlockLocation("overworld",3,70,4)
        first=BlockSnapshot(loc,block_entity=BlockEntitySnapshot("Chest",inventory=[
            InventorySlotSnapshot(2,{"Name":"minecraft:stone","Count":1}),
            InventorySlotSnapshot(0,{"Name":"minecraft:diamond","Count":1}),
        ],is_container=True,container_size=3),block_entity_status="captured")
        second=BlockSnapshot(loc,block_entity=BlockEntitySnapshot("Chest",inventory=[
            InventorySlotSnapshot(0,{"Name":"minecraft:diamond","Count":1}),
            InventorySlotSnapshot(2,{"Name":"minecraft:stone","Count":1}),
        ],is_container=True,container_size=3),block_entity_status="captured")
        self.assertEqual(first.refresh_revision(),second.refresh_revision())
    def test_revision_includes_capture_status_and_container_metadata(self):
        loc=BlockLocation("overworld",4,70,4)
        baseline=BlockSnapshot(loc,block_entity=BlockEntitySnapshot(
            "Chest",is_container=True,container_size=27
        ),block_entity_status="captured")
        baseline_revision=baseline.refresh_revision()
        status_changed=BlockSnapshot(loc,block_entity=BlockEntitySnapshot(
            "Chest",is_container=True,container_size=27
        ),block_entity_status="container_unavailable")
        self.assertNotEqual(baseline_revision,status_changed.refresh_revision())
        flag_changed=BlockSnapshot(loc,block_entity=BlockEntitySnapshot(
            "Chest",is_container=False,container_size=27
        ),block_entity_status="captured")
        self.assertNotEqual(baseline_revision,flag_changed.refresh_revision())
        capacity_changed=BlockSnapshot(loc,block_entity=BlockEntitySnapshot(
            "Chest",is_container=True,container_size=54
        ),block_entity_status="captured")
        self.assertNotEqual(baseline_revision,capacity_changed.refresh_revision())
    def test_empty_high_slot_capacity_change_updates_revision(self):
        svc=BlockDataService(); loc=BlockLocation("overworld",5,70,4)
        before=svc.capture(loc.dimension,(loc.x,loc.y,loc.z))
        first=BlockPatch(loc,before.revision,inventory_removals={5})
        self.assertTrue(svc.apply(first).ok)
        capacity_six=svc.capture(loc.dimension,(loc.x,loc.y,loc.z))
        self.assertEqual(capacity_six.block_entity.inventory,[])
        self.assertEqual(capacity_six.block_entity.container_size,6)
        second=BlockPatch(loc,capacity_six.revision,inventory_removals={10})
        self.assertTrue(svc.apply(second).ok)
        capacity_eleven=svc.capture(loc.dimension,(loc.x,loc.y,loc.z))
        self.assertEqual(capacity_eleven.block_entity.inventory,[])
        self.assertEqual(capacity_eleven.block_entity.container_size,11)
        self.assertNotEqual(capacity_six.revision,capacity_eleven.revision)
    def test_unsupported_conflict_policies_do_not_mutate(self):
        svc=BlockDataService(); before=svc.capture("overworld",(9,70,9))
        patch=BlockPatch(before.location,before.revision,state_updates={"facing":"south"})
        for policy in (ConflictPolicy.MERGE_CHANGED_PATHS,ConflictPolicy.MERGE_INVENTORY_SLOTS,ConflictPolicy.REPLACE):
            result=svc.apply(patch,policy)
            self.assertFalse(result.ok)
            self.assertEqual(result.status,"unsupported")
            self.assertEqual(result.resulting_revision,0)
            self.assertEqual(svc.capture("overworld",(9,70,9)).states,{})
    def test_capture_region_is_bounded(self):
        svc=BlockDataService()
        self.assertEqual(len(svc.capture_region("overworld",(5,6,7),(5,6,7))),1)
        with self.assertRaisesRegex(ValueError,"32768"):
            svc.capture_region("overworld",(0,0,0),(32768,0,0))
    def test_live_capture_region_delegates_once_and_normalizes_bounds(self):
        bridge=FakeLiveBridge()
        service=BlockDataService(LiveBlockDataAdapter(object(),bridge))
        snapshots=service.capture_region("overworld",(3,4,5),(1,2,3))
        self.assertEqual(len(snapshots),2)
        self.assertEqual(bridge.capture_calls,[])
        self.assertEqual(
            bridge.capture_region_calls,
            [("overworld",1,2,3,3,4,5)],
        )
        self.assertEqual(snapshots[0].location,BlockLocation("overworld",1,2,3))
    def test_falsey_adapters_and_bridges_are_not_replaced(self):
        adapter=FalseyInMemoryAdapter()
        self.assertIs(BlockDataService(adapter).adapter,adapter)
        bridge=FakeLiveBridge()
        self.assertIs(LiveBlockDataAdapter(object(),bridge).bridge,bridge)
    def test_shelf_view_reads_all_slots_and_builds_cas_patch(self):
        loc=BlockLocation("overworld",8,70,8)
        snapshot=BlockSnapshot(loc,block_entity=BlockEntitySnapshot(
            "minecraft:shelf",inventory=[
                InventorySlotSnapshot(1,{"Name":"minecraft:diamond","Count":2},77),
            ],is_container=True,container_size=3
        ),block_entity_status="captured",revision=1234)
        shelf=ShelfView(snapshot)
        self.assertEqual(shelf.kind,ShelfKind.SHELF)
        self.assertEqual(shelf.capacity,3)
        self.assertEqual(shelf.slots,[None,{"Name":"minecraft:diamond","Count":2},None])
        patch=shelf.patch_item(2,{"Name":"minecraft:emerald","Count":4})
        self.assertEqual(patch.expected_revision,1234)
        self.assertEqual(patch.inventory_updates[2]["Count"],4)
        with self.assertRaises(IndexError): shelf.clear_item(3)
    def test_chiseled_shelf_view_fails_closed(self):
        loc=BlockLocation("overworld",9,70,8)
        snapshot=BlockSnapshot(loc,block_entity=BlockEntitySnapshot(
            "minecraft:chiseled_bookshelf",is_container=True,container_size=6
        ),block_entity_status="captured",revision=10)
        shelf=ShelfView(snapshot)
        self.assertEqual(shelf.kind,ShelfKind.CHISELED_BOOKSHELF)
        shelf.patch_item(5,{"Name":"minecraft:written_book","Count":1})
        with self.assertRaisesRegex(ValueError,"exactly one"):
            shelf.patch_item(0,{"Name":"minecraft:written_book","Count":2})
        with self.assertRaisesRegex(ValueError,"exactly one"):
            shelf.patch_item(0,{"Name":"minecraft:diamond","Count":1})
        snapshot.block_entity.container_size=3
        with self.assertRaisesRegex(ValueError,"capacity"):
            ShelfView(snapshot)
    def test_shelf_batch_replace_and_detached_snapshot(self):
        loc=BlockLocation("overworld",10,70,8)
        snapshot=BlockSnapshot(loc,block_entity=BlockEntitySnapshot(
            "minecraft:shelf",inventory=[
                InventorySlotSnapshot(0,{"Name":"minecraft:diamond","Count":2}),
            ],is_container=True,container_size=3
        ),block_entity_status="captured",revision=20)
        shelf=ShelfView(snapshot)
        snapshot.block_entity.container_size=99
        snapshot.block_entity.inventory[0].item["Count"]=99
        self.assertEqual(shelf.capacity,3)
        self.assertEqual(shelf.get_item(0)["Count"],2)
        patch=shelf.patch_items(
            {1:{"Name":"minecraft:emerald","Count":3}},
            {0},
        )
        self.assertEqual(patch.expected_revision,20)
        self.assertEqual(patch.inventory_updates[1]["Count"],3)
        self.assertEqual(patch.inventory_removals,{0})
        replacement=shelf.replace_items([
            {"Name":"minecraft:stone","Count":1},None,
            {"Name":"minecraft:gold_ingot","Count":2},
        ])
        self.assertEqual(set(replacement.inventory_updates),{0,2})
        self.assertEqual(replacement.inventory_removals,{1})
        with self.assertRaisesRegex(ValueError,"updated and removed"):
            shelf.patch_items({0:{"Name":"minecraft:stone"}},{0})
        with self.assertRaisesRegex(ValueError,"exact capacity"):
            shelf.replace_items([None])
    def test_live_block_adapter_converts_typed_shelf_and_patch(self):
        bridge=FakeLiveBridge()
        adapter=LiveBlockDataAdapter(object(),bridge)
        self.assertTrue(adapter.available)
        self.assertEqual(adapter.capabilities()["adapter"],"exact")
        service=BlockDataService(adapter)
        snapshot=service.capture("overworld",(1,2,3))
        shelf=ShelfView(snapshot)
        self.assertEqual(shelf.get_item(0)["Name"],"minecraft:diamond")
        result=service.apply(shelf.clear_item(0))
        self.assertTrue(result.ok)
        self.assertEqual(bridge.applied[1],"fail_if_changed")
        self.assertEqual(bridge.applied[0]["inventory_removals"],[0])
    def test_shelf_shop_reserves_restores_and_replaces_stock(self):
        adapter=InMemoryAdapter()
        location=BlockLocation("overworld",20,70,20)
        snapshot=BlockSnapshot(location,block_entity=BlockEntitySnapshot(
            "minecraft:shelf",inventory=[
                InventorySlotSnapshot(0,{"Name":"minecraft:diamond","Count":5}),
            ],is_container=True,container_size=3
        ),block_entity_status="captured")
        snapshot.refresh_revision()
        adapter._blocks[location]=snapshot
        shop=ShelfShop(
            BlockDataService(adapter),location,
            {0:ShelfListing(0,"minecraft:diamond","minecraft:emerald",8)},
        )
        self.assertEqual(shop.quotes()[0].stock_count,5)
        reservation=shop.reserve(0,2)
        self.assertEqual(shop.quotes()[0].stock_count,3)
        detached_item=reservation.item
        detached_item["Count"]=99
        self.assertEqual(reservation.item["Count"],2)
        forged=StockReservation(
            "forged",location,0,
            {"Name":"minecraft:diamond","Count":1},1,
            reservation.shelf_revision,
        )
        with self.assertRaisesRegex(RuntimeError,"not active"):
            shop.restore(forged)
        altered=StockReservation(
            reservation.reservation_id,location,0,
            {"Name":"minecraft:diamond","Count":1},1,
            reservation.shelf_revision,
        )
        with self.assertRaisesRegex(RuntimeError,"does not match"):
            shop.restore(altered)
        self.assertEqual(shop.quotes()[0].stock_count,3)
        self.assertTrue(shop.restore(reservation).ok)
        self.assertEqual(shop.quotes()[0].stock_count,5)
        with self.assertRaisesRegex(RuntimeError,"already been restored"):
            shop.restore(reservation)
        self.assertTrue(shop.replace_stock([
            {"Name":"minecraft:diamond","Count":2},None,None,
        ]).ok)
        self.assertEqual(shop.quotes()[0].stock_count,2)
        completed=shop.reserve(0,1)
        altered_completed=StockReservation(
            completed.reservation_id,location,0,
            {"Name":"minecraft:gold_ingot","Count":1},1,
            completed.shelf_revision,
        )
        with self.assertRaisesRegex(RuntimeError,"does not match"):
            shop.complete(altered_completed)
        shop.complete(completed)
        self.assertEqual(shop.quotes()[0].stock_count,1)
        with self.assertRaisesRegex(RuntimeError,"already been completed"):
            shop.restore(completed)
        with self.assertRaisesRegex(RuntimeError,"already been completed"):
            shop.complete(completed)
if __name__=="__main__": unittest.main()
