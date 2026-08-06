from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
import re
from types import ModuleType, SimpleNamespace
import sys
import tomllib
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4


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
    event_module = ModuleType("endstone.event")
    form_module = ModuleType("endstone.form")
    plugin_module = ModuleType("endstone.plugin")

    def event_handler(func=None, **_kwargs):
        def decorate(handler):
            handler._is_event_handler = True
            return handler

        return decorate(func) if func is not None else decorate

    class PlayerQuitEvent:
        def __init__(self, player) -> None:
            self.player = player

    class PlayerDeathEvent:
        def __init__(self, player) -> None:
            self.player = player

    class Button:
        def __init__(self, text="", icon=None, on_click=None) -> None:
            self.text = text
            self.icon = icon
            self.on_click = on_click

    class ActionForm:
        def __init__(
            self,
            title="",
            content="",
            buttons=None,
            on_submit=None,
            on_close=None,
        ) -> None:
            self.title = title
            self.content = content
            self.buttons = list(buttons or [])
            self.on_submit = on_submit
            self.on_close = on_close

        def add_button(self, text, icon=None, on_click=None):
            self.buttons.append(Button(text, icon, on_click))
            return self

        def submit(self, player, selection) -> None:
            if self.on_submit is not None:
                self.on_submit(player, selection)
            if type(selection) is int and 0 <= selection < len(self.buttons):
                callback = self.buttons[selection].on_click
                if callback is not None:
                    callback(player)

        def close(self, player) -> None:
            if self.on_close is not None:
                self.on_close(player)

    class ModalForm:
        def __init__(
            self,
            title="",
            controls=None,
            submit_button=None,
            icon=None,
            on_submit=None,
            on_close=None,
        ) -> None:
            self.title = title
            self.controls = list(controls or [])
            self.submit_button = submit_button
            self.icon = icon
            self.on_submit = on_submit
            self.on_close = on_close

        def add_control(self, control):
            self.controls.append(control)
            return self

        def submit(self, player, values) -> None:
            response = values if isinstance(values, str) else json.dumps(values)
            if self.on_submit is not None:
                self.on_submit(player, response)

        def close(self, player) -> None:
            if self.on_close is not None:
                self.on_close(player)

    class Dropdown:
        def __init__(self, label="", options=None, default_index=None) -> None:
            self.label = label
            self.options = list(options or [])
            self.default_index = default_index

    class Slider:
        def __init__(
            self,
            label="",
            min=0,
            max=100,
            step=20,
            default_value=None,
        ) -> None:
            self.label = label
            self.min = min
            self.max = max
            self.step = step
            self.default_value = default_value

    class TextInput:
        def __init__(self, label="", placeholder="", default_value=None) -> None:
            self.label = label
            self.placeholder = placeholder
            self.default_value = default_value

    class Plugin:
        def __init__(self) -> None:
            self.server = object()
            self.logger = StrictEndstoneLogger()
            self.registered_events: list[tuple[str, type]] = []

        def register_events(self, listener) -> None:
            for name in dir(listener):
                handler = getattr(listener, name)
                function = getattr(handler, "__func__", handler)
                if not getattr(function, "_is_event_handler", False):
                    continue
                annotation = inspect.signature(handler).parameters["event"].annotation
                if isinstance(annotation, str):
                    raise TypeError("event handler annotations must be concrete")
                self.registered_events.append((name, annotation))

    class Command:
        def __init__(self, name: str):
            self.name = name

    class CommandSender:
        pass

    plugin_module.Plugin = Plugin
    event_module.PlayerDeathEvent = PlayerDeathEvent
    event_module.PlayerQuitEvent = PlayerQuitEvent
    event_module.event_handler = event_handler
    form_module.ActionForm = ActionForm
    form_module.Button = Button
    form_module.Dropdown = Dropdown
    form_module.ModalForm = ModalForm
    form_module.Slider = Slider
    form_module.TextInput = TextInput
    command_module.Command = Command
    command_module.CommandSender = CommandSender
    endstone_module.plugin = plugin_module
    endstone_module.command = command_module
    endstone_module.event = event_module
    endstone_module.form = form_module
    sys.modules["endstone"] = endstone_module
    sys.modules["endstone.plugin"] = plugin_module
    sys.modules["endstone.command"] = command_module
    sys.modules["endstone.event"] = event_module
    sys.modules["endstone.form"] = form_module


install_endstone_test_double()
sys.path.insert(0, str(PLUGIN_SOURCE))

from endstone_blockdata_inspector import (  # noqa: E402
    BlockDataInspectorPlugin,
    _bridge_loader,
)
from endstone.event import PlayerDeathEvent, PlayerQuitEvent  # noqa: E402
from endstone.form import ActionForm, ModalForm  # noqa: E402


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


class FakePlayer(FakeSender):
    def __init__(
        self, name: str = "Tester", unique_id: UUID | str | None = None
    ) -> None:
        super().__init__(name)
        self.unique_id = unique_id or f"uuid-{name.casefold()}"
        self.forms: list[ActionForm | ModalForm] = []
        self.permission = True
        self.dead = False
        self.fail_send: Exception | None = None

    @property
    def current_form(self) -> ActionForm | ModalForm:
        return self.forms[-1]

    def has_permission(self, permission: str) -> bool:
        return permission == "bd.admin" and self.permission

    def is_dead(self) -> bool:
        return self.dead

    def send_form(self, form: ActionForm | ModalForm) -> None:
        if self.fail_send is not None:
            raise self.fail_send
        self.forms.append(form)


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
                {
                    "slot": slot,
                    "item": copy.deepcopy(item),
                    "revision": snapshot["revision"] + 1,
                }
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
    def make_plugin(
        self,
    ) -> tuple[BlockDataInspectorPlugin, FakeLiveBridge, FakeSender]:
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
        plugin.active_forms = {}
        return plugin, bridge, FakeSender()

    def make_player_plugin(
        self, name: str = "Tester"
    ) -> tuple[BlockDataInspectorPlugin, FakeLiveBridge, FakePlayer]:
        plugin, bridge, _ = self.make_plugin()
        return plugin, bridge, FakePlayer(name)

    def test_packaging_uses_current_endstone_entry_point(self) -> None:
        metadata = tomllib.loads((PLUGIN_PROJECT / "pyproject.toml").read_text("utf-8"))
        project = metadata["project"]
        self.assertEqual(project["version"], "0.5.0")
        self.assertEqual(BlockDataInspectorPlugin.version, project["version"])
        self.assertEqual(project["requires-python"], "==3.14.*")
        self.assertEqual(project["dependencies"], ["endstone==0.11.7"])
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
            set(metadata["tool"]["setuptools"]["packages"]),
            {"endstone_blockdata_inspector", "endstone_blockdata"},
        )

    def test_bridge_loader_prefers_bundled_platform_module(self) -> None:
        bundled = ModuleType(_bridge_loader.BUNDLED_BRIDGE_MODULE)
        bundled.__version__ = BlockDataInspectorPlugin.version
        with patch.object(
            _bridge_loader.importlib, "import_module", return_value=bundled
        ) as import_module:
            loaded = _bridge_loader.import_live_bridge(BlockDataInspectorPlugin.version)

        self.assertIs(loaded, bundled)
        import_module.assert_called_once_with(_bridge_loader.BUNDLED_BRIDGE_MODULE)

    def test_bridge_loader_rejects_missing_or_mismatched_native_version(self) -> None:
        for bridge_version in (None, "0.4.8"):
            with self.subTest(bridge_version=bridge_version):
                bundled = ModuleType(_bridge_loader.BUNDLED_BRIDGE_MODULE)
                if bridge_version is not None:
                    bundled.__version__ = bridge_version
                with patch.object(
                    _bridge_loader.importlib,
                    "import_module",
                    return_value=bundled,
                ):
                    with self.assertRaisesRegex(RuntimeError, "matching platform wheel"):
                        _bridge_loader.import_live_bridge(
                            BlockDataInspectorPlugin.version
                        )

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
        self.assertEqual(
            set(plugin.registered_events),
            {
                ("on_player_death", PlayerDeathEvent),
                ("on_player_quit", PlayerQuitEvent),
            },
        )
        self.assertTrue(
            all(
                not isinstance(annotation, str)
                for _, annotation in plugin.registered_events
            )
        )

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
                "/bd (menu)<action: BlockDataMenuAction>",
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
            {"menu", "locate", "inspect", "item", "audit", "state"},
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
            ["menu"],
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

    def test_bare_bd_opens_player_menu_and_console_keeps_text_help(self) -> None:
        plugin, _, player = self.make_player_plugin()
        command = SimpleNamespace(name="bd")

        self.assertTrue(plugin.on_command(player, command, []))
        self.assertIsInstance(player.current_form, ActionForm)
        self.assertEqual(player.current_form.title, "BlockData Inspector")
        self.assertEqual(
            [button.text for button in player.current_form.buttons],
            [
                "Locate Containers",
                "Inspect / Select Target",
                "Container Inventory",
                "Audit Changes",
                "Block State",
                "Command Help",
                "Close",
            ],
        )
        token = plugin.active_forms[plugin._sender_key(player)]
        self.assertIsInstance(token, UUID)

        player.current_form.close(player)
        self.assertEqual(plugin.active_forms, {})
        self.assertTrue(plugin.on_command(player, command, ["menu"]))
        self.assertIsInstance(player.current_form, ActionForm)
        player.current_form.submit(player, 5)
        self.assertTrue(
            any(
                "BlockData Inspector Test Plugin" in message
                for message in player.messages
            )
        )
        self.assertEqual(player.current_form.title, "BlockData Inspector")
        player.current_form.submit(player, 6)
        self.assertEqual(plugin.active_forms, {})

        console = FakeSender("Console")
        self.assertTrue(plugin.on_command(console, command, []))
        self.assertTrue(
            any("BlockData Inspector" in message for message in console.messages)
        )
        self.assertTrue(plugin.on_command(console, command, ["menu"]))
        self.assertTrue(
            any("only available to players" in message for message in console.messages)
        )

    def test_form_lock_stale_callbacks_permissions_and_send_failure(self) -> None:
        plugin, _, player = self.make_player_plugin()

        self.assertTrue(plugin._show_main_menu(player))
        first_form = player.current_form
        first_token = plugin.active_forms[plugin._sender_key(player)]
        self.assertFalse(plugin._show_main_menu(player))
        self.assertEqual(len(player.forms), 1)
        self.assertIn("already open", player.messages[-1])

        first_form.close(player)
        self.assertEqual(plugin.active_forms, {})
        self.assertTrue(plugin._show_main_menu(player))
        current_form = player.current_form
        current_token = plugin.active_forms[plugin._sender_key(player)]
        self.assertNotEqual(first_token, current_token)

        first_form.submit(player, 0)
        self.assertIs(player.current_form, current_form)
        self.assertEqual(plugin.active_forms[plugin._sender_key(player)], current_token)

        player.permission = False
        current_form.submit(player, 0)
        self.assertEqual(plugin.active_forms, {})
        self.assertIs(player.current_form, current_form)
        self.assertIn("no longer have permission", player.messages[-1])

        player.permission = True
        player.fail_send = RuntimeError("client rejected form")
        self.assertFalse(plugin._show_main_menu(player))
        self.assertEqual(plugin.active_forms, {})
        self.assertIn("client rejected form", player.messages[-1])
        self.assertIn("client rejected form", plugin.logger.records[-1][1])

        player.fail_send = None
        player.dead = True
        self.assertFalse(plugin._show_main_menu(player))
        self.assertEqual(plugin.active_forms, {})
        self.assertIn("player is dead", player.messages[-1])

        player.dead = False
        self.assertTrue(plugin._show_main_menu(player))
        unavailable_form = player.current_form
        player.dead = True
        unavailable_form.submit(player, 0)
        self.assertEqual(plugin.active_forms, {})
        self.assertIs(player.current_form, unavailable_form)

    def test_form_permission_check_fails_closed_when_sender_cannot_check_it(
        self,
    ) -> None:
        plugin, _, _ = self.make_plugin()
        messages: list[str] = []
        sender = SimpleNamespace(
            unique_id=uuid4(),
            is_dead=False,
            send_form=lambda _form: self.fail("form must not be sent"),
            send_message=messages.append,
        )

        self.assertFalse(plugin._show_main_menu(sender))
        self.assertEqual(plugin.active_forms, {})
        self.assertIn("Unable to verify the bd.admin permission", messages[-1])

    def test_replacement_player_wrapper_shares_uuid_lock_and_stale_token_guard(
        self,
    ) -> None:
        plugin, _, first = self.make_player_plugin("First")
        shared_id = uuid4()
        first.unique_id = shared_id
        replacement = FakePlayer("Replacement", shared_id)

        self.assertTrue(plugin._show_main_menu(first))
        stale_form = first.current_form
        self.assertFalse(plugin._show_main_menu(replacement))
        self.assertEqual(replacement.forms, [])

        plugin.on_player_death(PlayerDeathEvent(replacement))
        self.assertEqual(plugin.active_forms, {})
        self.assertTrue(plugin._show_main_menu(replacement))
        current_token = plugin.active_forms[plugin._sender_key(replacement)]

        stale_form.submit(first, 0)
        self.assertEqual(
            plugin.active_forms[plugin._sender_key(replacement)], current_token
        )
        self.assertEqual(len(replacement.forms), 1)
        replacement.current_form.close(replacement)
        self.assertEqual(plugin.active_forms, {})

    def test_form_locks_are_per_player_and_clear_on_lifecycle_events(self) -> None:
        plugin, _, first = self.make_player_plugin("First")
        second = FakePlayer("Second")

        self.assertTrue(plugin._show_main_menu(first))
        self.assertTrue(plugin._show_main_menu(second))
        self.assertEqual(len(plugin.active_forms), 2)

        plugin.on_player_death(PlayerDeathEvent(first))
        self.assertNotIn(plugin._sender_key(first), plugin.active_forms)
        self.assertIn(plugin._sender_key(second), plugin.active_forms)

        self.assertTrue(plugin._show_main_menu(first))
        plugin.on_player_quit(PlayerQuitEvent(first))
        self.assertNotIn(plugin._sender_key(first), plugin.active_forms)

        plugin.on_disable()
        self.assertEqual(plugin.active_forms, {})

    def test_form_back_close_cancel_and_invalid_responses_keep_one_page(self) -> None:
        plugin, _, player = self.make_player_plugin()

        self.assertTrue(plugin._show_main_menu(player))
        player.current_form.submit(player, 1)
        self.assertEqual(player.current_form.title, "Inspect / Select Target")
        self.assertEqual(len(plugin.active_forms), 1)

        player.current_form.close(player)
        self.assertEqual(player.current_form.title, "BlockData Inspector")
        self.assertEqual(len(plugin.active_forms), 1)

        player.current_form.submit(player, 1)
        player.current_form.submit(player, 2)
        self.assertEqual(player.current_form.title, "BlockData Inspector")

        player.current_form.submit(player, 0)
        self.assertIsInstance(player.current_form, ModalForm)
        self.assertEqual(player.current_form.title, "Locate Containers")
        player.current_form.close(player)
        self.assertEqual(player.current_form.title, "BlockData Inspector")

        player.current_form.submit(player, 0)
        malformed = player.current_form
        malformed.submit(player, "{not json")
        self.assertIsInstance(player.current_form, ModalForm)
        self.assertIsNot(player.current_form, malformed)
        self.assertIn("invalid response", player.messages[-1])
        self.assertEqual(len(plugin.active_forms), 1)

        wrong_length = player.current_form
        wrong_length.submit(player, [5, 6])
        self.assertIsNot(player.current_form, wrong_length)
        self.assertIn("invalid response", player.messages[-1])

        wrong_type = player.current_form
        wrong_type.submit(player, ["5"])
        self.assertIsNot(player.current_form, wrong_type)
        self.assertIn("invalid response", player.messages[-1])

        player.current_form.close(player)
        invalid_main = player.current_form
        invalid_main.submit(player, 99)
        self.assertEqual(player.current_form.title, "BlockData Inspector")
        self.assertIsNot(player.current_form, invalid_main)
        self.assertIn("invalid selection", player.messages[-1])

        player.current_form.close(player)
        self.assertEqual(plugin.active_forms, {})

    def test_every_menu_action_dispatches_the_exact_existing_command_args(self) -> None:
        plugin, _, player = self.make_player_plugin()

        with patch.object(plugin, "_dispatch", return_value=True) as dispatch:
            self.assertTrue(plugin._show_main_menu(player))

            player.current_form.submit(player, 0)
            player.current_form.submit(player, [7])

            player.current_form.submit(player, 1)
            player.current_form.submit(player, 0)
            player.current_form.submit(player, 1)
            player.current_form.submit(player, ["10", "64", "8"])
            player.current_form.submit(player, 2)

            player.current_form.submit(player, 2)
            player.current_form.submit(player, 0)
            before_confirmation = dispatch.call_count
            player.current_form.submit(player, ["1", "diamond", "", ""])
            self.assertEqual(dispatch.call_count, before_confirmation)
            self.assertIn("Confirm", player.current_form.title)
            player.current_form.submit(player, 0)

            player.current_form.submit(player, 0)
            player.current_form.submit(
                player,
                ["2", "written_book", "", '{"display":{"Name":"Test"}}'],
            )
            player.current_form.submit(player, 0)

            player.current_form.submit(player, 1)
            player.current_form.submit(
                player,
                ["10", "64", "8", "3", "apple", "4", '{"foo":1}'],
            )
            player.current_form.submit(player, 0)

            player.current_form.submit(player, 2)
            player.current_form.submit(player, ["4"])
            player.current_form.submit(player, 0)

            player.current_form.submit(player, 3)
            player.current_form.submit(player, ["10", "64", "8", "5"])
            player.current_form.submit(player, 0)
            player.current_form.submit(player, 4)

            player.current_form.submit(player, 3)
            player.current_form.submit(player, 0)
            player.current_form.submit(player, 1)
            player.current_form.submit(player, 2)
            player.current_form.submit(player, [0, "10", "64", "8"])
            player.current_form.submit(player, 2)
            player.current_form.submit(player, [1, "10", "64", "8"])
            player.current_form.submit(player, 3)
            player.current_form.submit(player, 4)

            player.current_form.submit(player, 4)
            player.current_form.submit(player, 0)
            before_confirmation = dispatch.call_count
            player.current_form.submit(player, ["minecraft:open_bit", "true"])
            self.assertEqual(dispatch.call_count, before_confirmation)
            player.current_form.submit(player, 0)

            player.current_form.submit(player, 1)
            player.current_form.submit(
                player,
                ["minecraft:facing_direction", "2", "10", "64", "8"],
            )
            player.current_form.submit(player, 0)

        self.assertEqual(
            [call.args[1] for call in dispatch.call_args_list],
            [
                ["locate", "7"],
                ["inspect"],
                ["inspect", "10", "64", "8"],
                ["item", "add", "1", "diamond"],
                [
                    "item",
                    "add",
                    "2",
                    "written_book",
                    "1",
                    '{"display":{"Name":"Test"}}',
                ],
                [
                    "item",
                    "add",
                    "at",
                    "10",
                    "64",
                    "8",
                    "3",
                    "apple",
                    "4",
                    '{"foo":1}',
                ],
                ["item", "remove", "4"],
                ["item", "remove", "at", "10", "64", "8", "5"],
                ["audit", "start"],
                ["audit", "stop"],
                ["audit", "start", "10", "64", "8"],
                ["audit", "stop", "10", "64", "8"],
                ["audit", "history"],
                ["state", "set", "minecraft:open_bit", "true"],
                [
                    "state",
                    "set",
                    "minecraft:facing_direction",
                    "2",
                    "10",
                    "64",
                    "8",
                ],
            ],
        )

    def test_write_confirmations_cancel_without_dispatching(self) -> None:
        plugin, _, player = self.make_player_plugin()

        with patch.object(plugin, "_dispatch", return_value=True) as dispatch:
            self.assertTrue(plugin._show_inventory_menu(player))
            player.current_form.submit(player, 0)
            player.current_form.submit(player, ["1", "diamond", "1", ""])
            self.assertIn("Confirm", player.current_form.title)
            self.assertEqual(dispatch.call_count, 0)
            player.current_form.submit(player, 1)
            self.assertEqual(player.current_form.title, "Container Inventory")
            self.assertEqual(dispatch.call_count, 0)

            player.current_form.submit(player, 2)
            player.current_form.submit(player, ["1"])
            self.assertIn("Confirm", player.current_form.title)
            player.current_form.close(player)
            self.assertEqual(player.current_form.title, "Container Inventory")
            self.assertEqual(dispatch.call_count, 0)

            player.current_form.close(player)
            self.assertEqual(player.current_form.title, "BlockData Inspector")
            player.current_form.close(player)
            self.assertEqual(plugin.active_forms, {})

    def test_forms_reject_obvious_field_errors_before_dispatch_or_confirmation(
        self,
    ) -> None:
        cases = [
            (
                "inspect blank",
                lambda plugin, sender: plugin._show_inspect_at_form(sender),
                ["", "64", "8"],
            ),
            (
                "inspect noninteger",
                lambda plugin, sender: plugin._show_inspect_at_form(sender),
                ["x", "64", "8"],
            ),
            (
                "negative slot",
                lambda plugin, sender: plugin._show_item_add_form(
                    sender, explicit=False
                ),
                ["-1", "diamond", "1", ""],
            ),
            (
                "zero count",
                lambda plugin, sender: plugin._show_item_add_form(
                    sender, explicit=False
                ),
                ["1", "diamond", "0", ""],
            ),
            (
                "non-object nbt",
                lambda plugin, sender: plugin._show_item_add_form(
                    sender, explicit=False
                ),
                ["1", "diamond", "1", "[]"],
            ),
            (
                "remove slot",
                lambda plugin, sender: plugin._show_item_remove_form(
                    sender, explicit=False
                ),
                ["slot"],
            ),
            (
                "audit coordinate",
                lambda plugin, sender: plugin._show_audit_at_form(sender),
                [0, "x", "64", "8"],
            ),
            (
                "state coordinate",
                lambda plugin, sender: plugin._show_state_set_form(
                    sender, explicit=True
                ),
                ["open_bit", "true", "x", "64", "8"],
            ),
        ]

        for label, opener, response in cases:
            with self.subTest(label=label):
                plugin, _, player = self.make_player_plugin()
                with patch.object(plugin, "_dispatch", return_value=True) as dispatch:
                    self.assertTrue(opener(plugin, player))
                    original_form = player.current_form
                    original_form.submit(player, response)
                dispatch.assert_not_called()
                self.assertIsInstance(player.current_form, ModalForm)
                self.assertIsNot(player.current_form, original_form)
                self.assertEqual(len(plugin.active_forms), 1)

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
        chest_line = next(
            message for message in sender.messages if "minecraft:chest" in message
        )
        barrel_line = next(
            message for message in sender.messages if "minecraft:barrel" in message
        )
        shulker_line = next(
            message
            for message in sender.messages
            if "minecraft:red_shulker_box" in message
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

    def test_inspect_bounds_large_canonical_nbt_and_keeps_inventory_summary(
        self,
    ) -> None:
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

    def test_inspect_distinguishes_unavailable_empty_and_nested_storage_contents(
        self,
    ) -> None:
        plugin, bridge, sender = self.make_plugin()
        contents_key = plugin._STORAGE_ITEM_CONTENTS_KEY
        nested_bundle = {
            "Name": "minecraft:red_bundle",
            "Count": 1,
            "tag": {
                contents_key: [
                    {
                        "Slot": 3,
                        "Name": "minecraft:emerald",
                        "Count": 4,
                    }
                ]
            },
        }
        outer_bundle = {
            "Name": "minecraft:bundle",
            "Count": 1,
            "tag": {
                contents_key: [
                    {
                        "Slot": 0,
                        "Name": "minecraft:diamond",
                        "Count": 2,
                    },
                    {"Slot": 1, **nested_bundle},
                ]
            },
        }
        snapshot = container_snapshot(
            "minecraft:chest",
            "Chest",
            20,
            inventory=[
                {
                    "slot": 0,
                    "item": {"Name": "minecraft:bundle", "Count": 1},
                    "revision": 1,
                },
                {
                    "slot": 1,
                    "item": {
                        "Name": "minecraft:blue_bundle",
                        "Count": 1,
                        "tag": {contents_key: []},
                    },
                    "revision": 1,
                },
                {"slot": 2, "item": outer_bundle, "revision": 1},
                {
                    "slot": 3,
                    "item": {
                        "Name": "minecraft:yellow_bundle",
                        "Count": 1,
                        "tag": [],
                    },
                    "revision": 1,
                },
            ],
        )
        bridge.snapshots[("overworld", 20, 64, 8)] = snapshot

        self.assertTrue(
            plugin.on_command(
                sender,
                SimpleNamespace(name="bd"),
                ["inspect", "20", "64", "8"],
            )
        )
        output = "\n".join(sender.messages)
        self.assertIn("Bundle / Storage Item Contents:", output)
        self.assertIn(
            "Container slot 0 minecraft:bundle: contents unavailable", output
        )
        self.assertIn(
            "Container slot 1 minecraft:blue_bundle: contents empty", output
        )
        self.assertIn(
            "Container slot 2 minecraft:bundle: 2 serialized entries", output
        )
        self.assertIn(
            "Container slot 3 minecraft:yellow_bundle: contents unavailable "
            "(item tag is not a compound)",
            output,
        )
        self.assertIn("[0] minecraft:diamond x2", output)
        self.assertIn("Nested minecraft:red_bundle: 1 serialized entry", output)
        self.assertIn("[3] minecraft:emerald x4", output)

    def test_storage_contents_summary_has_depth_entry_line_and_text_bounds(
        self,
    ) -> None:
        plugin, _, _ = self.make_plugin()
        contents_key = plugin._STORAGE_ITEM_CONTENTS_KEY

        def nested_bundle(depth: int) -> dict:
            contents: list[dict] = []
            if depth:
                contents.append({"Slot": 0, **nested_bundle(depth - 1)})
            return {
                "Name": "minecraft:bundle",
                "Count": 1,
                "tag": {contents_key: contents},
            }

        root = nested_bundle(plugin._MAX_STORAGE_SUMMARY_DEPTH + 2)
        root["tag"][contents_key].extend(
            {
                "Slot": slot,
                "Name": "minecraft:written_book",
                "Count": 1,
                "tag": {"display": {"Name": "x" * 500}},
            }
            for slot in range(1, 12)
        )
        lines = plugin._storage_item_summary_lines(
            [{"slot": 4, "item": root, "revision": 1}]
        )

        self.assertLessEqual(len(lines), plugin._MAX_STORAGE_SUMMARY_LINES)
        self.assertTrue(
            all(
                len(line) <= plugin._MAX_STORAGE_ITEM_LABEL_CHARS
                for line in lines
            )
        )
        self.assertTrue(any("omitted at depth 4" in line for line in lines))
        self.assertTrue(any("and 4 more serialized entries" in line for line in lines))

    def test_inspect_reports_shelf_and_chiseled_bookshelf_diagnostics(self) -> None:
        plugin, bridge, sender = self.make_plugin()
        shelf = container_snapshot(
            "minecraft:oak_shelf",
            "minecraft:block_actor_59",
            21,
            capacity=3,
            inventory=[item_slot(2, "minecraft:diamond_pickaxe")],
        )
        shelf["block_entity"]["nbt"]["_endstone_actor_type"] = 59
        chiseled = container_snapshot(
            "minecraft:chiseled_bookshelf",
            "minecraft:block_actor_51",
            22,
            capacity=6,
            inventory=[item_slot(5, "minecraft:written_book")],
        )
        chiseled["block_entity"]["nbt"]["_endstone_actor_type"] = 51
        missing = {
            "location": {
                "dimension": "overworld",
                "x": 23,
                "y": 64,
                "z": 8,
            },
            "type": "minecraft:spruce_shelf",
            "runtime_id": 59,
            "states": {},
            "revision": 1,
            "block_entity_status": "container_unavailable",
            "block_entity": None,
        }
        bridge.snapshots[("overworld", 21, 64, 8)] = shelf
        bridge.snapshots[("overworld", 22, 64, 8)] = chiseled
        bridge.snapshots[("overworld", 23, 64, 8)] = missing

        command = SimpleNamespace(name="bd")
        self.assertTrue(plugin.on_command(sender, command, ["inspect", "21", "64", "8"]))
        output = "\n".join(sender.messages)
        self.assertIn("Shelf / Chiseled Bookshelf Diagnostics", output)
        self.assertIn(
            "Actor: minecraft:block_actor_59; expected BlockActorType 59 / Shelf",
            output,
        )
        self.assertIn(
            "Capacity: live 3; expected 3; valid slots 0-2; occupied slots: 2",
            output,
        )
        self.assertIn("general item stacks", output)
        self.assertIn("powered hotbar swaps", output)

        sender.messages.clear()
        self.assertTrue(plugin.on_command(sender, command, ["inspect", "22", "64", "8"]))
        output = "\n".join(sender.messages)
        self.assertIn(
            "expected BlockActorType 51 / ChiseledBookshelf", output
        )
        self.assertIn("valid slots 0-5; occupied slots: 5", output)
        self.assertIn(
            "book, writable_book, written_book, or enchanted_book only", output
        )
        self.assertIn("Comparator behavior", output)

        sender.messages.clear()
        self.assertTrue(plugin.on_command(sender, command, ["inspect", "23", "64", "8"]))
        output = "\n".join(sender.messages)
        self.assertIn("Actor: unavailable; expected BlockActorType 59 / Shelf", output)
        self.assertIn("Capacity: live unavailable; expected 3", output)
        self.assertIn("status=container_unavailable", output)
        self.assertIn("block actor/inventory was not captured", output)

    def test_shelf_capacity_mismatch_is_prominent_and_shelf_is_a_candidate(
        self,
    ) -> None:
        plugin, _, _ = self.make_plugin()
        snapshot = container_snapshot(
            "minecraft:bamboo_shelf",
            "minecraft:shelf",
            24,
            capacity=4,
        )
        diagnostics = "\n".join(plugin._shelf_diagnostic_lines(snapshot))
        self.assertIn("live 4 (MISMATCH; expected adapter to fail closed)", diagnostics)
        self.assertTrue(plugin._looks_like_container_block(snapshot))

    def test_mutations_require_selection_and_item_at_forms_target_coordinates(
        self,
    ) -> None:
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

        self.assertTrue(plugin.on_command(sender, command, ["inspect", "8", "64", "8"]))
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
        self.assertTrue(
            any("retry the command" in message for message in sender.messages)
        )


if __name__ == "__main__":
    unittest.main()
