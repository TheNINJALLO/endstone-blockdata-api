from __future__ import annotations

import copy
import logging
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
import tomllib
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_PROJECT = ROOT / "examples" / "python" / "block_data_inspector_plugin"
PLUGIN_SOURCE = PLUGIN_PROJECT / "src"


def install_endstone_test_double() -> None:
    """Provide only the Endstone surface needed by handler unit tests."""

    endstone_module = ModuleType("endstone")
    command_module = ModuleType("endstone.command")
    plugin_module = ModuleType("endstone.plugin")

    class Plugin:
        def __init__(self) -> None:
            self.server = object()
            self.logger = logging.getLogger(type(self).__name__)

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

from endstone_blockdata_inspector import BlockDataInspectorPlugin


class FakeSender:
    def __init__(self) -> None:
        self.location = SimpleNamespace(
            x=8,
            y=64,
            z=8,
            dimension=SimpleNamespace(name="overworld"),
        )
        self.messages: list[str] = []

    def send_message(self, message: str) -> None:
        self.messages.append(message)


class FakeLiveBridge:
    def __init__(self) -> None:
        self.available_now = True
        self.availability_checks = 0
        self.snapshot = {
            "location": {"dimension": "overworld", "x": 8, "y": 64, "z": 8},
            "type": "minecraft:chest",
            "runtime_id": 54,
            "states": {"minecraft:cardinal_direction": "north"},
            "revision": 1,
            "block_entity": {
                "type": "Chest",
                "nbt": {"CustomName": "Test Chest"},
                "snbt": "{}",
                "canonical": True,
                "inventory": [],
            },
        }
        self.last_patch = None
        self.last_policy = None
        self.conflict_next = False

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
        snapshot = copy.deepcopy(self.snapshot)
        snapshot["location"] = {
            "dimension": dimension,
            "x": x,
            "y": y,
            "z": z,
        }
        return snapshot

    def capture_region(self, server, dimension, *bounds):
        del server, dimension, bounds
        return [copy.deepcopy(self.snapshot)]

    def apply(self, server, patch, conflict_policy="fail_if_changed"):
        del server
        self.last_patch = copy.deepcopy(patch)
        self.last_policy = conflict_policy
        if conflict_policy != "fail_if_changed":
            return {
                "ok": False,
                "status": "invalid_policy",
                "message": "expected fail_if_changed",
                "resulting_revision": self.snapshot["revision"],
            }
        if self.conflict_next:
            self.conflict_next = False
            self.snapshot["revision"] += 1
        if patch.get("expected_revision") != self.snapshot["revision"]:
            return {
                "ok": False,
                "status": "conflict",
                "message": "revision changed",
                "resulting_revision": self.snapshot["revision"],
            }

        self.snapshot["states"].update(patch.get("state_updates", {}))
        inventory = {
            int(entry["slot"]): entry
            for entry in self.snapshot["block_entity"]["inventory"]
        }
        for slot in patch.get("inventory_removals", []):
            inventory.pop(int(slot), None)
        for slot, item in patch.get("inventory_updates", {}).items():
            inventory[int(slot)] = {
                "slot": int(slot),
                "item": copy.deepcopy(item),
                "revision": self.snapshot["revision"] + 1,
            }
        self.snapshot["block_entity"]["inventory"] = list(inventory.values())
        self.snapshot["revision"] += 1
        return {
            "ok": True,
            "status": "applied",
            "message": "applied",
            "resulting_revision": self.snapshot["revision"],
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

    def test_all_commands_permissions_and_usages_are_declared(self) -> None:
        self.assertEqual(BlockDataInspectorPlugin.api_version, "0.11")
        self.assertEqual(BlockDataInspectorPlugin.depend, ["blockdata_api"])
        self.assertEqual(set(BlockDataInspectorPlugin.commands), {"bd"})
        command = BlockDataInspectorPlugin.commands["bd"]
        self.assertEqual(command["aliases"], ["blockdata"])
        self.assertEqual(command["permissions"], ["bd.admin"])
        self.assertEqual(
            set(BlockDataInspectorPlugin._SUBCOMMAND_HANDLERS),
            {"locate", "inspect", "item", "audit", "state"},
        )
        usages = "\n".join(command["usages"])
        for subcommand in BlockDataInspectorPlugin._SUBCOMMAND_HANDLERS:
            self.assertIn(f"({subcommand})", usages)
        self.assertNotIn("[args...]", usages)
        self.assertEqual(
            BlockDataInspectorPlugin.permissions["bd.admin"]["default"], "op"
        )

    def test_every_registered_handler_runs_against_live_bridge_contract(self) -> None:
        plugin, bridge, sender = self.make_plugin()
        command = SimpleNamespace(name="bd")

        self.assertTrue(plugin.on_command(sender, command, []))
        self.assertTrue(plugin.on_command(sender, command, ["locate", "0"]))
        self.assertTrue(plugin.on_command(sender, command, ["inspect", "8", "64", "8"]))
        self.assertTrue(
            plugin.on_command(
                sender,
                command,
                ["item", "add", "0", "diamond", "2", '{"display":{"Name":"Test"}}'],
            )
        )
        self.assertEqual(
            bridge.last_patch["inventory_updates"][0]["id"], "minecraft:diamond"
        )
        self.assertEqual(bridge.last_policy, "fail_if_changed")
        self.assertTrue(plugin.on_command(sender, command, ["audit", "start"]))
        bridge.snapshot["block_entity"]["inventory"][0]["item"]["count"] = 3
        bridge.snapshot["revision"] += 1
        self.assertTrue(plugin.on_command(sender, command, ["audit", "stop"]))
        self.assertTrue(plugin.on_command(sender, command, ["audit", "history"]))
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
        self.assertTrue(plugin.on_command(sender, command, ["item", "remove", "0"]))
        self.assertEqual(bridge.last_patch["inventory_removals"], [0])
        self.assertTrue(
            plugin.on_command(sender, SimpleNamespace(name="blockdata"), [])
        )
        self.assertFalse(plugin.on_command(sender, SimpleNamespace(name="other"), []))
        self.assertTrue(any("live" in message.lower() for message in sender.messages))
        self.assertFalse(any("Â§" in message for message in sender.messages))

    def test_missing_bridge_fails_clearly_without_memory_fallback(self) -> None:
        plugin, _, sender = self.make_plugin()
        plugin.live_bridge = None
        plugin.bridge_error = "module not found"
        with patch(
            "endstone_blockdata_inspector.plugin.importlib.import_module",
            side_effect=ModuleNotFoundError("module not found"),
        ):
            self.assertTrue(
                plugin.on_command(sender, SimpleNamespace(name="bd"), ["inspect"])
            )
        self.assertIn("Native BlockData service unavailable", sender.messages[-1])

    def test_command_retries_bridge_after_late_service_registration(self) -> None:
        plugin = BlockDataInspectorPlugin()
        bridge = FakeLiveBridge()
        bridge.available_now = False
        sender = FakeSender()

        with patch(
            "endstone_blockdata_inspector.plugin.importlib.import_module",
            return_value=bridge,
        ):
            plugin.on_enable()
            self.assertIsNone(plugin.live_bridge)
            self.assertEqual(bridge.availability_checks, 1)

            bridge.available_now = True
            self.assertTrue(
                plugin.on_command(sender, SimpleNamespace(name="bd"), ["inspect"])
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
                ["state", "set", "minecraft:cardinal_direction", "south"],
            )
        )
        self.assertEqual(bridge.last_policy, "fail_if_changed")
        self.assertEqual(bridge.snapshot["states"], original_states)
        self.assertTrue(any("retry the command" in message for message in sender.messages))


if __name__ == "__main__":
    unittest.main()
