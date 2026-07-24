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
if __name__=="__main__": unittest.main()
