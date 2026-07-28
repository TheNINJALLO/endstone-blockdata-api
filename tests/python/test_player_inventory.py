import unittest

from endstone_blockdata.player_inventory import (
    LivePlayerInventoryAdapter,
    PlayerInventorySection,
    PlayerInventorySnapshot,
    PlayerInventoryView,
)


def item(identifier: str, count: int = 1):
    return {"Name": identifier, "Count": count}


class FakeBridge:
    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.last_patch = None

    def player_inventory_available(self, _server):
        return True

    def player_inventory_capabilities(self, _server):
        return {
            "adapter": "fake",
            "main": True,
            "armor": True,
            "offhand": True,
            "ender_chest": True,
            "item_user_nbt": True,
        }

    def capture_player_inventory(self, _server, _player):
        return self.snapshot

    def apply_player_inventory(self, _server, _player, patch, policy):
        self.last_patch = patch
        return {
            "ok": True,
            "status": "applied",
            "message": policy,
            "resulting_revision": 124,
        }


class PlayerInventoryTests(unittest.TestCase):
    def setUp(self):
        bundle = item("minecraft:bundle")
        bundle["tag"] = {
            "storage_item_component_content": [
                {**item("minecraft:diamond", 3), "Slot": 0}
            ]
        }
        self.raw = {
            "player_name": "Josh",
            "xuid": "1234",
            "selected_hotbar_slot": 2,
            "main_size": 36,
            "armor_size": 4,
            "offhand_size": 1,
            "ender_chest_size": 27,
            "main": [
                {"slot": 2, "item": bundle, "revision": 11},
                {"slot": 8, "item": item("minecraft:stone", 64), "revision": 12},
            ],
            "armor": [
                {"slot": 0, "item": item("minecraft:diamond_helmet"), "revision": 13}
            ],
            "offhand": [
                {"slot": 0, "item": item("minecraft:shield"), "revision": 14}
            ],
            "ender_chest": [],
            "revision": 123,
        }
        self.snapshot = PlayerInventorySnapshot.from_mapping(self.raw)
        self.view = PlayerInventoryView(self.snapshot)

    def test_reads_all_sections(self):
        self.assertEqual(self.view.get_item(PlayerInventorySection.MAIN, 8)["Count"], 64)
        self.assertEqual(self.view.get_item(PlayerInventorySection.ARMOR, 0)["Name"],
                         "minecraft:diamond_helmet")
        self.assertEqual(self.view.get_item(PlayerInventorySection.OFFHAND, 0)["Name"],
                         "minecraft:shield")
        self.assertIsNone(self.view.get_item(PlayerInventorySection.ENDER_CHEST, 4))

    def test_finds_and_patches_bundle_in_player_inventory(self):
        refs = self.view.find_storage_items()
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].section, PlayerInventorySection.MAIN)
        self.assertEqual(refs[0].slot, 2)

        bundle = self.view.storage_item(PlayerInventorySection.MAIN, 2)
        bundle.set_item(1, item("minecraft:emerald", 4))
        patch = self.view.patch_storage_item(PlayerInventorySection.MAIN, 2, bundle)
        self.assertEqual(patch.expected_revision, 123)
        contents = patch.main_updates[2]["tag"]["storage_item_component_content"]
        self.assertEqual(len(contents), 2)

    def test_armor_offhand_and_ender_chest_patches(self):
        armor = self.view.patch_item(PlayerInventorySection.ARMOR, 1,
                                     item("minecraft:diamond_chestplate"))
        self.assertIn(1, armor.armor_updates)

        offhand = self.view.clear_item(PlayerInventorySection.OFFHAND, 0)
        self.assertEqual(offhand.offhand_removals, {0})

        ender = self.view.patch_item(PlayerInventorySection.ENDER_CHEST, 5,
                                    item("minecraft:gold_ingot", 8))
        self.assertIn(5, ender.ender_chest_updates)

    def test_slot_bounds(self):
        with self.assertRaises(IndexError):
            self.view.get_item(PlayerInventorySection.ARMOR, 4)
        with self.assertRaises(IndexError):
            self.view.patch_item(PlayerInventorySection.OFFHAND, 1, item("minecraft:stone"))

    def test_live_bridge_wrapper(self):
        bridge = FakeBridge(self.raw)
        adapter = LivePlayerInventoryAdapter(object(), bridge)
        self.assertTrue(adapter.available)
        self.assertEqual(adapter.capabilities()["adapter"], "fake")
        captured = adapter.capture(object())
        self.assertEqual(captured.player_name, "Josh")
        patch = PlayerInventoryView(captured).clear_item(PlayerInventorySection.MAIN, 8)
        result = adapter.apply(object(), patch)
        self.assertTrue(result["ok"])
        self.assertEqual(bridge.last_patch["main_removals"], [8])


if __name__ == "__main__":
    unittest.main()
