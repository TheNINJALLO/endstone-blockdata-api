import sys, unittest
sys.path.insert(0,"python")
from endstone_blockdata import *
class TestBlockData(unittest.TestCase):
    def test_patch_conflict_and_audit(self):
        svc=BlockDataService(); before=svc.capture("overworld",(1,64,2))
        p=BlockPatch(before.location,before.revision,"minecraft:chest",nbt_updates={"CustomName":"Vault"},inventory_updates={0:{"Name":"minecraft:diamond","Count":4,"tag":{"display":{"Name":"Protected"}}}})
        self.assertTrue(svc.apply(p).ok)
        after=svc.capture("overworld",(1,64,2)); self.assertEqual(ContainerView(after).get_item(0)["Count"],4)
        delta=svc.diff(before,after); self.assertEqual(delta.inventory_changes[0].kind,InventoryChangeKind.ADDED)
        self.assertFalse(svc.apply(p).ok)
    def test_revision_is_independent_of_inventory_storage_order(self):
        loc=BlockLocation("overworld",3,70,4)
        first=BlockSnapshot(loc,block_entity=BlockEntitySnapshot("Chest",inventory=[
            InventorySlotSnapshot(2,{"Name":"minecraft:stone","Count":1}),
            InventorySlotSnapshot(0,{"Name":"minecraft:diamond","Count":1}),
        ]))
        second=BlockSnapshot(loc,block_entity=BlockEntitySnapshot("Chest",inventory=[
            InventorySlotSnapshot(0,{"Name":"minecraft:diamond","Count":1}),
            InventorySlotSnapshot(2,{"Name":"minecraft:stone","Count":1}),
        ]))
        self.assertEqual(first.refresh_revision(),second.refresh_revision())
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
if __name__=="__main__": unittest.main()
