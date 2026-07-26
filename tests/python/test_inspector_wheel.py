from __future__ import annotations

import copy
import json
from pathlib import Path
import re
from types import ModuleType, SimpleNamespace
import sys
import tomllib
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_PROJECT = ROOT / "examples" / "python" / "block_data_inspector_plugin"
PLUGIN_SOURCE = PLUGIN_PROJECT / "src"


class StrictEndstoneLogger:
    """Match Endstone's one-rendered-string Python logger contract."""

    def __init__(self) -> None:
        self.records: list[tuple[str, str]] = []

    def info(self, message: str) -> None:
        self.records.append(("info", message))

    def error(self, message: str) -> None:
        self.records.append(("error", message))


def install_endstone_test_double() -> None:
    """Provide only the Endstone surface needed by handler unit tests."""

    endstone_module = ModuleType("endstone")
    command_module = ModuleType("endstone.command")
    plugin_module = ModuleType("endstone.plugin")

    class Plugin:
        def __init__(self) -> None:
            self.server = object()
            self.logger = StrictEndstoneLogger()

    class Command:
        def __init__(self, name: str):
            self.name = name

    class CommandSender:
        pass

    plugin_module.Plugin = Plugin
    command_module.Command = Command
    command_module.CommandSender = CommandSender
    endstone_module.plugin = plugin_module
    endstone_module.command = command_module
    sys.modules["endstone"] = endstone_module
    sys.modules["endstone.plugin"] = plugin_module
    sys.modules["endstone.command"] = command_module


install_endstone_test_double()
sys.path.insert(0, str(PLUGIN_SOURCE))

from endstone_blockdata_inspector import BlockDataInspectorPlugin, _bridge_loader


class FakeSender:
    def __init__(self, name: str = "Tester") -> None:
        self.name = name
        self.location = SimpleNamespace(
            x=8,
            y=64,
            z=8,
            dimension=SimpleNamespace(name="overworld"),
        )
        self.messages: list[str] = []

    def send_message(self, message: str) -> None:
        self.messages.append(message)


def item_slot(
    slot: int, item_id: str, count: int = 1, *, custom_name: str | None = None
) -> dict:
    item = {"Name": item_id, "Count": count}
    if custom_name:
        item["tag"] = {"display": {"Name": custom_name}}
    return {"slot": slot, "item": item, "revision": 1}


def container_snapshot(
    block_type: str,
    actor_type: str,
    x: int,
    *,
    capacity: int = 27,
    inventory: list[dict] | None = None,
) -> dict:
    return {
        "location": {"dimension": "overworld", "x": x, "y": 64, "z": 8},
        "type": block_type,
        "runtime_id": 54,
        "states": {"minecraft:cardinal_direction": "north"},
        "revision": 1,
        "block_entity_status": "captured",
        "block_entity": {
            "type": actor_type,
            "nbt": {"CustomName": f"Test {actor_type}"},
            "snbt": "{}",
            "canonical": True,
            "is_container": True,
            "container_size": capacity,
            "inventory": list(inventory or []),
        },
    }


class FakeLiveBridge:
    def __init__(self) -> None:
        self.available_now = True
        self.availability_checks = 0
        snapshots = [
            container_snapshot(
                "minecraft:chest",
                "Chest",
                8,
                inventory=[
                    item_slot(0, "minecraft:diamond", 2, custom_name="Starter Gems")
                ],
            ),
            container_snapshot("minecraft:barrel", "Barrel", 10),
            container_snapshot(
                "minecraft:red_shulker_box",
                "ShulkerBox",
                12,
                inventory=[item_slot(5, "minecraft:stone", 32)],
            ),
            {
                "location": {
                    "dimension": "overworld",
                    "x": 9,
                    "y": 64,
                    "z": 8,
                },
                "type": "minecraft:oak_sign",
                "runtime_id": 63,
                "states": {},
                "revision": 1,
                "block_entity_status": "captured",
                "block_entity": {
                    "type": "Sign",
                    "nbt": {"Text": "Not a container"},
                    "snbt": "{}",
                    "canonical": True,
                    "is_container": False,
                    "container_size": 0,
                    "inventory": [],
                },
            },
            {
                "location": {
                    "dimension": "overworld",
                    "x": 14,
                    "y": 64,
                    "z": 8,
                },
                "type": "minecraft:trapped_chest",
                "runtime_id": 146,
                "states": {},
                "revision": 1,
                "block_entity_status": "no_actor",
                "block_entity": None,
            },
        ]
        self.snapshots = {
            (
                snapshot["location"]["dimension"],
                snapshot["location"]["x"],
                snapshot["location"]["y"],
                snapshot["location"]["z"],
            ): snapshot
            for snapshot in snapshots
        }
        self.last_patch = None
        self.last_policy = None
        self.conflict_next = False
        self.capture_calls: list[tuple[str, int, int, int]] = []
        self.region_calls: list[tuple[str, tuple[int, ...]]] = []

    @property
    def snapshot(self) -> dict:
        return self.snapshots[("overworld", 8, 64, 8)]

    def snapshot_at(self, x: int, y: int = 64, z: int = 8) -> dict:
        return self.snapshots[("overworld", x, y, z)]

    def set_item(self, x: int, slot: int, item: dict | None) -> None:
        snapshot = self.snapshot_at(x)
        inventory = snapshot["block_entity"]["inventory"]
        inventory[:] = [entry for entry in inventory if int(entry["slot"]) != slot]
        if item is not None:
            inventory.append(
                {"slot": slot, "item": copy.deepcopy(item), "revision": snapshot["revision"] + 1}
            )
        snapshot["revision"] += 1

    def available(self, server):
        del server
        self.availability_checks += 1
        return self.available_now

    def capabilities(self, server):
        del server
        return {
            "adapter": "test",
            "block_entity_nbt": True,
            "block_writes": True,
            "inventory": True,
        }

    def capture(self, server, dimension, x, y, z):
        del server
        key = (dimension, x, y, z)
        self.capture_calls.append(key)
        snapshot = self.snapshots.get(key)
        return copy.deepcopy(snapshot) if snapshot is not None else None

    def capture_region(self, server, dimension, *bounds):
        del server
        self.region_calls.append((dimension, tuple(bounds)))
        min_x, min_y, min_z, max_x, max_y, max_z = bounds
        return [
            copy.deepcopy(snapshot)
            for (entry_dimension, x, y, z), snapshot in self.snapshots.items()
            if entry_dimension == dimension
            and min_x <= x <= max_x
            and min_y <= y <= max_y
            and min_z <= z <= max_z
        ]

    def apply(self, server, patch, conflict_policy="fail_if_changed"):
        del server
        self.last_patch = copy.deepcopy(patch)
        self.last_policy = conflict_policy
        location = patch["location"]
        key = (
            location["dimension"],
            int(location["x"]),
            int(location["y"]),
            int(location["z"]),
        )
        snapshot = self.snapshots.get(key)
        if snapshot is None:
            return {
                "ok": False,
                "status": "invalid_target",
                "message": "missing target",
                "resulting_revision": 0,
            }
        if conflict_policy != "fail_if_changed":
            return {
                "ok": False,
                "status": "invalid_policy",
                "message": "expected fail_if_changed",
                "resulting_revision": snapshot["revision"],
            }
        if self.conflict_next:
            self.conflict_next = False
            snapshot["revision"] += 1
        if patch.get("expected_revision") != snapshot["revision"]:
            return {
                "ok": False,
                "status": "conflict",
                "message": "revision changed",
                "resulting_revision": snapshot["revision"],
            }

        snapshot["states"].update(patch.get("state_updates", {}))
        inventory = {
            int(entry["slot"]): entry
            for entry in (snapshot.get("block_entity") or {}).get("inventory", [])
        }
        for slot in patch.get("inventory_removals", []):
            inventory.pop(int(slot), None)
        for slot, item in patch.get("inventory_updates", {}).items():
            inventory[int(slot)] = {
                "slot": int(slot),
                "item": copy.deepcopy(item),
                "revision": snapshot["revision"] + 1,
            }
        if snapshot.get("block_entity") is not None:
            snapshot["block_entity"]["inventory"] = list(inventory.values())
        snapshot["revision"] += 1
        return {
            "ok": True,
            "status": "applied",
            "message": "applied",
            "resulting_revision": snapshot["revision"],
        }


class InspectorWheelTests(unittest.TestCase):
    def make_plugin(self) -> tuple[BlockDataInspectorPlugin, FakeLiveBridge, FakeSender]:
        plugin = BlockDataInspectorPlugin()
        bridge = FakeLiveBridge()
        plugin.live_bridge = bridge
        plugin.bridge_error = ""
        plugin.native_capabilities = {
            "adapter": "test",
            "block_entity_nbt": True,
            "block_writes": True,
            "inventory": True,
        }
        plugin.selected_targets = {}
        plugin.audit_baselines = {}
        plugin.audit_logs = []
        return plugin, bridge, FakeSender()

    def test_packaging_uses_current_endstone_entry_point(self) -> None:
        metadata = tomllib.loads((PLUGIN_PROJECT / "pyproject.toml").read_text("utf-8"))
        project = metadata["project"]
        self.assertEqual(project["requires-python"], "==3.14.*")
        self.assertEqual(project["dependencies"], ["endstone==0.11.6"])
        self.assertEqual(
            project["entry-points"]["endstone"],
            {
                "blockdata-inspector": (
                    "endstone_blockdata_inspector:BlockDataInspectorPlugin"
                )
            },
        )
        self.assertNotIn("endstone.plugins", project["entry-points"])
        self.assertEqual(
            metadata["tool"]["setuptools"]["packages"],
            ["endstone_blockdata_inspector"],
        )

    def test_bridge_loader_prefers_bundled_platform_module(self) -> None:
        bundled = ModuleType(_bridge_loader.BUNDLED_BRIDGE_MODULE)
        with patch.object(
            _bridge_loader.importlib, "import_module", return_value=bundled
        ) as import_module:
            loaded = _bridge_loader.import_live_bridge(BlockDataInspectorPlugin.version)

        self.assertIs(loaded, bundled)
        import_module.assert_called_once_with(_bridge_loader.BUNDLED_BRIDGE_MODULE)

    def test_bridge_loader_rejects_stale_top_level_module(self) -> None:
        bundled_missing = ModuleNotFoundError(
            "bundled bridge is absent", name=_bridge_loader.BUNDLED_BRIDGE_MODULE
        )
        stale_legacy = ModuleType(_bridge_loader.BRIDGE_MODULE)
        with patch.dict(sys.modules, {_bridge_loader.BRIDGE_MODULE: stale_legacy}):
            with patch.object(
                _bridge_loader.importlib,
                "import_module",
                side_effect=bundled_missing,
            ) as import_module:
                with self.assertRaises(ModuleNotFoundError) as raised:
                    _bridge_loader.import_live_bridge(BlockDataInspectorPlugin.version)

        self.assertIn("package-local native bridge", str(raised.exception))
        import_module.assert_called_once_with(_bridge_loader.BUNDLED_BRIDGE_MODULE)

    def test_bridge_loader_does_not_mask_bundled_dependency_errors(self) -> None:
        dependency_error = ModuleNotFoundError(
            "bundled dependency is absent", name="endstone.internal_dependency"
        )
        with patch.object(
            _bridge_loader.importlib, "import_module", side_effect=dependency_error
        ) as import_module:
            with self.assertRaises(ModuleNotFoundError) as raised:
                _bridge_loader.import_live_bridge(BlockDataInspectorPlugin.version)

        self.assertIs(raised.exception, dependency_error)
        import_module.assert_called_once_with(_bridge_loader.BUNDLED_BRIDGE_MODULE)

    def test_bridge_loader_missing_error_names_required_platform_wheel(self) -> None:
        missing = ModuleNotFoundError(
            "bundled bridge is absent", name=_bridge_loader.BUNDLED_BRIDGE_MODULE
        )
        with patch.object(
            _bridge_loader.importlib, "import_module", side_effect=missing
        ):
            with self.assertRaises(ModuleNotFoundError) as raised:
                _bridge_loader.import_live_bridge(BlockDataInspectorPlugin.version)

        message = str(raised.exception)
        self.assertIn(BlockDataInspectorPlugin.version, message)
        self.assertIn("CPython 3.14 platform wheel", message)
        self.assertIn("py3-none-any", message)

    def test_on_enable_uses_single_string_endstone_logger_methods(self) -> None:
        plugin = BlockDataInspectorPlugin()
        bridge = FakeLiveBridge()
        with patch(
            "endstone_blockdata_inspector.plugin.import_live_bridge",
            return_value=bridge,
        ):
            plugin.on_enable()

        self.assertEqual(plugin.logger.records[-1][0], "info")
        self.assertIn("native adapter 'test'", plugin.logger.records[-1][1])

        unavailable = BlockDataInspectorPlugin()
        with patch(
            "endstone_blockdata_inspector.plugin.import_live_bridge",
            side_effect=RuntimeError("bridge load failed"),
        ):
            unavailable.on_enable()

        self.assertEqual(unavailable.logger.records[-1][0], "error")
        self.assertIn("bridge load failed", unavailable.logger.records[-1][1])

    def test_all_commands_permissions_and_usages_are_declared(self) -> None:
        self.assertEqual(BlockDataInspectorPlugin.api_version, "0.11")
        self.assertEqual(BlockDataInspectorPlugin.depend, ["blockdata_api"])
        self.assertEqual(set(BlockDataInspectorPlugin.commands), {"bd"})
        command = BlockDataInspectorPlugin.commands["bd"]
        self.assertEqual(command["aliases"], ["blockdata"])
        self.assertEqual(command["permissions"], ["bd.admin"])
        self.assertEqual(
            command["usages"],
            [
                "/bd",
                "/bd (locate)<action: BlockDataLocateAction> [radius: int]",
                "/bd (inspect)<action: BlockDataInspectAction>",
                (
                    "/bd (inspect)<action: BlockDataInspectAtAction> "
                    "<x: int> <y: int> <z: int>"
                ),
                (
                    "/bd (item)<action: BlockDataItemAddAction> "
                    "(add)<operation: BlockDataItemAddOperation> <slot: int> "
                    "<item_id: str> [count: int] [nbt: json]"
                ),
                (
                    "/bd (item)<action: BlockDataItemAddAtAction> "
                    "(add)<operation: BlockDataItemAddAtOperation> "
                    "(at)<target: BlockDataItemAddAtTarget> "
                    "<x: int> <y: int> <z: int> <slot: int> "
                    "<item_id: str> [count: int] [nbt: json]"
                ),
                (
                    "/bd (item)<action: BlockDataItemRemoveAction> "
                    "(remove)<operation: BlockDataItemRemoveOperation> <slot: int>"
                ),
                (
                    "/bd (item)<action: BlockDataItemRemoveAtAction> "
                    "(remove)<operation: BlockDataItemRemoveAtOperation> "
                    "(at)<target: BlockDataItemRemoveAtTarget> "
                    "<x: int> <y: int> <z: int> <slot: int>"
                ),
                (
                    "/bd (audit)<action: BlockDataAuditToggleAction> "
                    "(start|stop)<operation: BlockDataAuditToggleOperation>"
                ),
                (
                    "/bd (audit)<action: BlockDataAuditToggleAtAction> "
                    "(start|stop)<operation: BlockDataAuditToggleAtOperation> "
                    "<x: int> <y: int> <z: int>"
                ),
                (
                    "/bd (audit)<action: BlockDataAuditHistoryAction> "
                    "(history)<operation: BlockDataAuditHistoryOperation>"
                ),
                (
                    "/bd (state)<action: BlockDataStateSetAction> "
                    "(set)<operation: BlockDataStateSetOperation> "
                    "<property: str> <value: str>"
                ),
                (
                    "/bd (state)<action: BlockDataStateSetAtAction> "
                    "(set)<operation: BlockDataStateSetAtOperation> "
                    "<property: str> <value: str> <x: int> <y: int> <z: int>"
                ),
            ],
        )
        self.assertEqual(
            set(BlockDataInspectorPlugin._SUBCOMMAND_HANDLERS),
            {"locate", "inspect", "item", "audit", "state"},
        )
        usages = "\n".join(command["usages"])
        self.assertNotIn("block_pos", usages)
        self.assertNotIn("[args...]", usages)
        enum_names = re.findall(r"\([^)]*\)<[^:>]+:\s*([^>]+)>", usages)
        self.assertEqual(len(enum_names), len(set(enum_names)))
        self.assertEqual(
            BlockDataInspectorPlugin.permissions["bd.admin"]["default"], "op"
        )

    def test_each_registered_overload_dispatches_to_a_handler(self) -> None:
        plugin, bridge, sender = self.make_plugin()
        command = SimpleNamespace(name="bd")
        invocations = [
            [],
            ["locate"],
            ["inspect"],
            ["inspect", "8", "64", "8"],
            ["item", "add", "1", "emerald"],
            ["item", "add", "at", "10", "64", "8", "1", "apple"],
            ["item", "remove", "1"],
            ["item", "remove", "at", "10", "64", "8", "1"],
            ["audit", "start"],
            ["audit", "stop"],
            ["audit", "start", "10", "64", "8"],
            ["audit", "stop", "10", "64", "8"],
            ["audit", "history"],
            ["state", "set", "minecraft:cardinal_direction", "south"],
            [
                "state",
                "set",
                "minecraft:cardinal_direction",
                "north",
                "10",
                "64",
                "8",
            ],
        ]

        for args in invocations:
            with self.subTest(args=args):
                self.assertTrue(plugin.on_command(sender, command, args))
        self.assertEqual(bridge.last_patch["location"]["x"], 10)

    def test_locate_filters_containers_selects_nearest_and_reports_misses(self) -> None:
        plugin, bridge, sender = self.make_plugin()
        command = SimpleNamespace(name="bd")

        self.assertTrue(plugin.on_command(sender, command, []))
        self.assertTrue(plugin.on_command(sender, command, ["locate", "12"]))
        output = "\n".join(sender.messages)
        self.assertIn("Found 3 supported container actors", output)
        self.assertIn("minecraft:chest", output)
        self.assertIn("minecraft:barrel", output)
        self.assertIn("minecraft:red_shulker_box", output)
        self.assertNotIn("minecraft:oak_sign", output)
        chest_line = next(message for message in sender.messages if "minecraft:chest" in message)
        barrel_line = next(message for message in sender.messages if "minecraft:barrel" in message)
        shulker_line = next(
            message for message in sender.messages if "minecraft:red_shulker_box" in message
        )
        self.assertIn("Capacity: §b27", chest_line)
        self.assertIn("Occupied: §b1", chest_line)
        self.assertIn("minecraft:diamond x2", chest_line)
        self.assertIn("Capacity: §b27", barrel_line)
        self.assertIn("Occupied: §b0", barrel_line)
        self.assertIn("Items: §fempty", barrel_line)
        self.assertIn("Capacity: §b27", shulker_line)
        self.assertIn("Occupied: §b1", shulker_line)
        self.assertIn("minecraft:stone x32", shulker_line)
        self.assertIn("actor/inventory capture missed", output)
        self.assertIn("status=no_actor", output)
        self.assertEqual(
            plugin.selected_targets[plugin._sender_key(sender)],
            ("overworld", 8, 64, 8),
        )
        self.assertTrue(
            plugin.on_command(sender, SimpleNamespace(name="blockdata"), [])
        )
        self.assertFalse(plugin.on_command(sender, SimpleNamespace(name="other"), []))
        self.assertFalse(any("Â§" in message for message in sender.messages))

    def test_locate_floors_negative_fractional_player_coordinates(self) -> None:
        plugin, bridge, sender = self.make_plugin()
        sender.location.x = -0.25
        sender.location.y = 63.9
        sender.location.z = -16.01

        self.assertTrue(
            plugin.on_command(sender, SimpleNamespace(name="bd"), ["locate", "0"])
        )
        self.assertEqual(
            bridge.region_calls[-1],
            ("overworld", (-1, 63, -17, -1, 63, -17)),
        )

    def test_inspect_uses_selected_target_and_hides_empty_slots(self) -> None:
        plugin, bridge, sender = self.make_plugin()
        command = SimpleNamespace(name="bd")

        self.assertTrue(
            plugin.on_command(sender, command, ["inspect", "10", "64", "8"])
        )
        output = "\n".join(sender.messages)
        self.assertIn("Container Capacity: §b27", output)
        self.assertIn("Occupied: §b0", output)
        self.assertIn("Occupied Contents: §oEmpty", output)
        self.assertNotIn("{'empty': True}", output)
        self.assertEqual(
            plugin.selected_targets[plugin._sender_key(sender)],
            ("overworld", 10, 64, 8),
        )

        sender.messages.clear()
        self.assertTrue(plugin.on_command(sender, command, ["inspect"]))
        self.assertEqual(bridge.capture_calls[-1], ("overworld", 10, 64, 8))

        sender.messages.clear()
        self.assertTrue(
            plugin.on_command(sender, command, ["inspect", "12", "64", "8"])
        )
        output = "\n".join(sender.messages)
        self.assertIn("minecraft:stone x32", output)
        self.assertNotIn("empty", output.casefold())

    def test_inspect_bounds_large_canonical_nbt_and_keeps_inventory_summary(self) -> None:
        plugin, bridge, sender = self.make_plugin()
        command = SimpleNamespace(name="bd")
        snapshot = bridge.snapshots[("overworld", 12, 64, 8)]
        large_nbt = {
            "Items": [
                {
                    "Slot": 5,
                    "Name": "minecraft:shulker_box",
                    "tag": {"payload": "x" * 5000},
                }
            ]
        }
        snapshot["block_entity"]["nbt"] = large_nbt

        self.assertTrue(
            plugin.on_command(sender, command, ["inspect", "12", "64", "8"])
        )
        canonical = next(
            message for message in sender.messages if "Canonical NBT" in message
        )
        expected_characters = len(
            json.dumps(large_nbt, default=str, separators=(",", ":"))
        )
        self.assertIn(f"{expected_characters} chars", canonical)
        self.assertIn("preview truncated", canonical)
        self.assertIn("[TRUNCATED;", canonical)
        self.assertLessEqual(
            len(canonical), plugin._MAX_CANONICAL_NBT_PREVIEW_CHARS + 80
        )
        self.assertIn("minecraft:stone x32", "\n".join(sender.messages))

    def test_mutations_require_selection_and_item_at_forms_target_coordinates(self) -> None:
        plugin, bridge, sender = self.make_plugin()
        command = SimpleNamespace(name="bd")

        self.assertTrue(
            plugin.on_command(
                sender,
                command,
                ["item", "add", "1", "diamond"],
            )
        )
        self.assertIsNone(bridge.last_patch)
        self.assertIn("No active container target", sender.messages[-1])
        self.assertTrue(
            plugin.on_command(
                sender,
                command,
                ["state", "set", "minecraft:cardinal_direction", "south"],
            )
        )
        self.assertIsNone(bridge.last_patch)
        self.assertTrue(plugin.on_command(sender, command, ["audit", "start"]))
        self.assertEqual(plugin.audit_baselines, {})

        self.assertTrue(
            plugin.on_command(
                sender,
                command,
                [
                    "item",
                    "add",
                    "at",
                    "10",
                    "64",
                    "8",
                    "1",
                    "gold_ingot",
                    "3",
                    '{"display":{"Name":"Test Gold"}}',
                ],
            )
        )
        self.assertEqual(
            bridge.last_patch["location"],
            {"dimension": "overworld", "x": 10, "y": 64, "z": 8},
        )
        self.assertEqual(
            bridge.last_patch["inventory_updates"][1]["id"],
            "minecraft:gold_ingot",
        )
        self.assertEqual(bridge.last_policy, "fail_if_changed")

        self.assertTrue(
            plugin.on_command(
                sender,
                command,
                ["item", "remove", "at", "12", "64", "8", "5"],
            )
        )
        self.assertEqual(bridge.last_patch["location"]["x"], 12)
        self.assertEqual(bridge.last_patch["inventory_removals"], [5])

        self.assertTrue(
            plugin.on_command(sender, command, ["inspect", "8", "64", "8"])
        )
        self.assertTrue(
            plugin.on_command(sender, command, ["item", "add", "1", "emerald"])
        )
        self.assertEqual(bridge.last_patch["location"]["x"], 8)
        self.assertEqual(
            bridge.last_patch["inventory_updates"][1]["id"], "minecraft:emerald"
        )
        self.assertTrue(
            plugin.on_command(
                sender,
                command,
                ["state", "set", "minecraft:cardinal_direction", "south"],
            )
        )
        self.assertEqual(
            bridge.last_patch["state_updates"],
            {"minecraft:cardinal_direction": "south"},
        )

    def test_audit_ignores_empty_markers_and_reports_sparse_transitions(self) -> None:
        plugin, bridge, sender = self.make_plugin()
        command = SimpleNamespace(name="bd")

        before = container_snapshot(
            "minecraft:barrel",
            "Barrel",
            10,
            inventory=[{"slot": 4, "item": {"empty": True}, "revision": 1}],
        )
        after = container_snapshot(
            "minecraft:barrel",
            "Barrel",
            10,
            inventory=[item_slot(4, "minecraft:apple", 2)],
        )
        self.assertEqual(
            plugin._diff_snapshots(before, after)["inventory_changes"][0]["kind"],
            "added",
        )
        self.assertEqual(
            plugin._diff_snapshots(after, before)["inventory_changes"][0]["kind"],
            "removed",
        )

        self.assertTrue(
            plugin.on_command(sender, command, ["inspect", "10", "64", "8"])
        )
        self.assertTrue(plugin.on_command(sender, command, ["audit", "start"]))
        bridge.set_item(10, 0, {"Name": "minecraft:apple", "Count": 1})
        self.assertTrue(plugin.on_command(sender, command, ["audit", "stop"]))
        self.assertTrue(any("[added]" in message for message in sender.messages))

        self.assertTrue(plugin.on_command(sender, command, ["audit", "start"]))
        bridge.set_item(10, 0, None)
        self.assertTrue(plugin.on_command(sender, command, ["audit", "stop"]))
        self.assertTrue(any("[removed]" in message for message in sender.messages))
        self.assertTrue(plugin.on_command(sender, command, ["audit", "history"]))

    def test_malformed_coordinates_and_invalid_targets_fail_closed(self) -> None:
        plugin, bridge, sender = self.make_plugin()
        command = SimpleNamespace(name="bd")

        for args in (
            ["inspect", "8", "64"],
            ["inspect", "bad", "64", "8"],
            ["audit", "start", "8", "64"],
            ["state", "set", "facing", "north", "8", "64"],
            ["item", "add", "at", "8", "64", "8"],
            ["item", "remove", "at", "8", "64", "8"],
        ):
            calls_before = len(bridge.capture_calls)
            self.assertTrue(plugin.on_command(sender, command, args))
            self.assertEqual(len(bridge.capture_calls), calls_before)

        self.assertTrue(
            plugin.on_command(sender, command, ["inspect", "99", "64", "8"])
        )
        self.assertEqual(bridge.capture_calls[-1], ("overworld", 99, 64, 8))
        self.assertIn("could not capture", sender.messages[-1])

        self.assertTrue(
            plugin.on_command(
                sender,
                command,
                ["item", "add", "at", "9", "64", "8", "0", "stone"],
            )
        )
        self.assertIn("not a supported container", sender.messages[-1])
        self.assertTrue(
            plugin.on_command(
                sender,
                command,
                ["item", "add", "at", "14", "64", "8", "0", "stone"],
            )
        )
        self.assertIn("no_actor", sender.messages[-1])
        self.assertTrue(
            plugin.on_command(
                sender,
                command,
                ["item", "add", "at", "10", "64", "8", "27", "stone"],
            )
        )
        self.assertIn("capacity of 27", sender.messages[-1])

    def test_missing_bridge_fails_clearly_without_memory_fallback(self) -> None:
        plugin, _, sender = self.make_plugin()
        plugin.live_bridge = None
        plugin.bridge_error = "module not found"
        with patch(
            "endstone_blockdata_inspector.plugin.import_live_bridge",
            side_effect=ModuleNotFoundError("module not found"),
        ):
            self.assertTrue(
                plugin.on_command(
                    sender,
                    SimpleNamespace(name="bd"),
                    ["inspect", "8", "64", "8"],
                )
            )
        self.assertIn("Native BlockData service unavailable", sender.messages[-1])

    def test_command_retries_bridge_after_late_service_registration(self) -> None:
        plugin = BlockDataInspectorPlugin()
        bridge = FakeLiveBridge()
        bridge.available_now = False
        sender = FakeSender()

        with patch(
            "endstone_blockdata_inspector.plugin.import_live_bridge",
            return_value=bridge,
        ):
            plugin.on_enable()
            self.assertIsNone(plugin.live_bridge)
            self.assertEqual(bridge.availability_checks, 1)

            bridge.available_now = True
            self.assertTrue(
                plugin.on_command(
                    sender,
                    SimpleNamespace(name="bd"),
                    ["inspect", "8", "64", "8"],
                )
            )

        self.assertIs(plugin.live_bridge, bridge)
        self.assertEqual(bridge.availability_checks, 2)
        self.assertEqual(plugin.native_capabilities["adapter"], "test")
        self.assertTrue(any("Live Block" in message for message in sender.messages))

    def test_revision_conflict_is_reported_without_forcing_write(self) -> None:
        plugin, bridge, sender = self.make_plugin()
        bridge.conflict_next = True
        original_states = copy.deepcopy(bridge.snapshot["states"])
        self.assertTrue(
            plugin.on_command(
                sender,
                SimpleNamespace(name="bd"),
                [
                    "state",
                    "set",
                    "minecraft:cardinal_direction",
                    "south",
                    "8",
                    "64",
                    "8",
                ],
            )
        )
        self.assertEqual(bridge.last_policy, "fail_if_changed")
        self.assertEqual(bridge.snapshot["states"], original_states)
        self.assertTrue(any("retry the command" in message for message in sender.messages))


if __name__ == "__main__":
    unittest.main()
