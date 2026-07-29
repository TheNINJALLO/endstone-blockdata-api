import unittest

from endstone_blockdata.model import BlockLocation, BlockSnapshot
from endstone_blockdata.storage_item import (
    StorageItemEntry,
    StorageItemRules,
    StorageItemStatus,
    StorageItemView,
    is_storage_item_nbt,
    make_max_stack_size_weight_resolver,
    validate_storage_item,
)


def item(identifier: str, count: int = 1):
    return {"Name": identifier, "Count": count}


class StorageItemTests(unittest.TestCase):
    def setUp(self):
        self.resolver = make_max_stack_size_weight_resolver({
            "minecraft:diamond": 64,
            "minecraft:stone": 64,
            "minecraft:ender_pearl": 16,
            "minecraft:netherite_sword": 1,
        })

    def test_reads_and_writes_bundle_contents(self):
        view = StorageItemView(item("minecraft:bundle"), create_if_missing=True)
        view.set_item(3, item("minecraft:diamond", 16))
        self.assertEqual(view.get_item(3)["Count"], 16)
        self.assertEqual(view.contents[0].slot, 3)
        view.clear_item(3)
        self.assertIsNone(view.get_item(3))

    def test_exact_weight_and_overweight(self):
        view = StorageItemView(item("minecraft:bundle"), create_if_missing=True)
        view.set_item(0, item("minecraft:diamond", 16))
        view.set_item(1, item("minecraft:ender_pearl", 4))
        result = view.validate(self.resolver)
        self.assertEqual(result.status, StorageItemStatus.VALID)
        self.assertEqual(result.used_weight, 32)
        self.assertTrue(result.exact_weight)

        view.set_item(2, item("minecraft:netherite_sword"))
        self.assertEqual(view.validate(self.resolver).status, StorageItemStatus.OVERWEIGHT)

    def test_nested_bundle_and_shulker_guard(self):
        inner = StorageItemView(item("minecraft:bundle"), create_if_missing=True)
        inner.set_item(0, item("minecraft:diamond", 4))
        outer = StorageItemView(item("minecraft:bundle"), create_if_missing=True)
        outer.set_item(0, inner.item)
        result = outer.validate(self.resolver)
        self.assertEqual(result.status, StorageItemStatus.VALID)
        self.assertEqual(result.used_weight, 8)

        outer.set_item(1, item("minecraft:purple_shulker_box"))
        self.assertEqual(outer.validate(self.resolver).status, StorageItemStatus.FORBIDDEN_ITEM)

    def test_custom_storage_item_and_patch(self):
        view = StorageItemView(item("ninjos:backpack"), create_if_missing=True)
        view.replace_contents([StorageItemEntry(0, item("minecraft:stone", 64))])
        snapshot = BlockSnapshot(BlockLocation("overworld", 1, 2, 3), revision=99)
        patch = view.patch_parent(snapshot, 5)
        self.assertEqual(patch.expected_revision, 99)
        self.assertEqual(patch.inventory_updates[5]["Name"], "ninjos:backpack")

    def test_duplicate_slot_and_nested_disabled(self):
        raw = item("minecraft:bundle")
        raw["tag"] = {"storage_item_component_content": [
            {**item("minecraft:diamond"), "Slot": 0},
            {**item("minecraft:stone"), "Slot": 0},
        ]}
        self.assertEqual(validate_storage_item(raw, weight_resolver=self.resolver).status,
                         StorageItemStatus.DUPLICATE_SLOT)

        inner = StorageItemView(item("minecraft:bundle"), create_if_missing=True).item
        outer = StorageItemView(item("minecraft:bundle"),
                                StorageItemRules(allow_nested_storage_items=False),
                                create_if_missing=True)
        outer.set_item(0, inner)
        self.assertEqual(outer.validate(self.resolver).status,
                         StorageItemStatus.NESTED_STORAGE_DISABLED)

    def test_missing_bundle_contents_fail_closed(self):
        raw = item("minecraft:bundle")
        self.assertTrue(is_storage_item_nbt(raw))

        result = validate_storage_item(raw, weight_resolver=self.resolver)
        self.assertEqual(result.status, StorageItemStatus.CONTENTS_UNAVAILABLE)
        self.assertEqual(result.message, "storage item contents are unavailable")
        self.assertFalse(result.ok)

        with self.assertRaisesRegex(ValueError, "contents are unavailable"):
            StorageItemView(raw)
        self.assertNotIn("tag", raw)

    def test_explicit_creation_initializes_a_genuinely_empty_bundle(self):
        raw = item("minecraft:bundle")
        view = StorageItemView(raw, create_if_missing=True)

        self.assertEqual(view.contents, [])
        self.assertEqual(view.item["tag"]["storage_item_component_content"], [])
        self.assertEqual(view.validate(self.resolver).status, StorageItemStatus.VALID)
        self.assertNotIn("tag", raw)

    def test_nested_bundle_with_unavailable_contents_is_not_empty(self):
        outer = StorageItemView(item("minecraft:bundle"), create_if_missing=True)
        outer.set_item(0, item("minecraft:bundle"))

        result = outer.validate(self.resolver)
        self.assertEqual(result.status, StorageItemStatus.CONTENTS_UNAVAILABLE)
        self.assertFalse(result.ok)

    def test_malformed_bundle_tag_is_invalid_not_unavailable(self):
        raw = {**item("minecraft:bundle"), "tag": "not-a-compound"}

        result = validate_storage_item(raw, weight_resolver=self.resolver)
        self.assertEqual(result.status, StorageItemStatus.INVALID_CONTENTS)
        with self.assertRaisesRegex(ValueError, "tag must be an NBT compound"):
            StorageItemView(raw, create_if_missing=True)

    def test_storage_item_rules_require_integer_not_boolean_values(self):
        invalid_rules = (
            {"slot_capacity": True},
            {"slot_capacity": 3.5},
            {"max_weight": False},
            {"max_weight": 32.0},
            {"nested_storage_item_weight": True},
            {"nested_storage_item_weight": 1.5},
        )
        for arguments in invalid_rules:
            with self.subTest(arguments=arguments):
                with self.assertRaises(ValueError):
                    StorageItemRules(**arguments)


if __name__ == "__main__":
    unittest.main()
