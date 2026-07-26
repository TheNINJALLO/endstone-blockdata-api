"""Endstone BlockData live-service command test plugin."""

from __future__ import annotations

import json
import math
from typing import Any

from endstone.command import Command, CommandSender
from endstone.plugin import Plugin

from ._bridge_loader import import_live_bridge


class BlockDataInspectorPlugin(Plugin):
    """Exercise the native BlockData service from in-game commands."""

    api_version = "0.11"
    version = "0.4.5-beta.32"
    description = "Interactive in-game container, NBT, and block-state test suite"
    depend = ["blockdata_api"]

    commands = {
        "bd": {
            "description": "BlockData inspector and container NBT test suite",
            "usages": [
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
            "aliases": ["blockdata"],
            "permissions": ["bd.admin"],
        }
    }

    permissions = {
        "bd.admin": {
            "description": "Allows access to BlockData Inspector commands",
            "default": "op",
        }
    }

    _SUBCOMMAND_HANDLERS = {
        "locate": "_handle_locate",
        "inspect": "_handle_inspect",
        "item": "_handle_item",
        "audit": "_handle_audit",
        "state": "_handle_state",
    }

    _KNOWN_CONTAINER_BLOCKS = frozenset(
        {
            "minecraft:barrel",
            "minecraft:blast_furnace",
            "minecraft:brewing_stand",
            "minecraft:chest",
            "minecraft:chiseled_bookshelf",
            "minecraft:dispenser",
            "minecraft:dropper",
            "minecraft:furnace",
            "minecraft:hopper",
            "minecraft:smoker",
            "minecraft:trapped_chest",
        }
    )
    _MAX_CANONICAL_NBT_PREVIEW_CHARS = 768

    def on_enable(self) -> None:
        self.selected_targets: dict[str, tuple[str, int, int, int]] = {}
        self.audit_baselines: dict[
            tuple[str, str, int, int, int], dict[str, Any]
        ] = {}
        self.audit_logs: list[dict[str, Any]] = []
        self.live_bridge = None
        self.native_capabilities: dict[str, Any] = {}
        self.bridge_error = "native bridge was not initialized"
        self._connect_bridge()

        if self.live_bridge is None:
            self.logger.error(
                f"BlockData live bridge unavailable; /bd commands will report unavailable: "
                f"{self.bridge_error}"
            )
        else:
            adapter = self.native_capabilities.get("adapter", "unknown")
            self.logger.info(
                f"BlockData Inspector enabled against native adapter '{adapter}'. "
                "Type '/bd' for help."
            )

    def _connect_bridge(self) -> Any | None:
        """Connect to the native service, allowing command-time recovery."""
        try:
            bridge = import_live_bridge(self.version)
            if not bridge.available(self.server):
                self.live_bridge = None
                self.native_capabilities = {}
                self.bridge_error = "endstone:blockdata:v2 native service is not registered"
                return None
            capabilities = dict(bridge.capabilities(self.server))
        except Exception as error:
            self.live_bridge = None
            self.native_capabilities = {}
            self.bridge_error = str(error)
            return None

        self.live_bridge = bridge
        self.native_capabilities = capabilities
        self.bridge_error = ""
        return bridge

    def on_command(
        self, sender: CommandSender, command: Command, args: list[str]
    ) -> bool:
        if command.name not in {"bd", "blockdata"}:
            return False
        if not args:
            self._send_help(sender)
            return True

        handler_name = self._SUBCOMMAND_HANDLERS.get(args[0].lower())
        if handler_name is None:
            self._send_help(sender)
            return True
        return getattr(self, handler_name)(sender, args[1:])

    def _send_help(self, sender: CommandSender) -> None:
        sender.send_message("§e=== BlockData Inspector Test Plugin (v0.4.5-beta.32) ===")
        sender.send_message("§a/bd locate [radius] §7- Find and select the nearest container")
        sender.send_message("§a/bd inspect [x y z] §7- Inspect/select a live container target")
        sender.send_message("§a/bd item add <slot> <id> [count] [nbt] §7- Add at selected target")
        sender.send_message(
            "§a/bd item add at <x> <y> <z> <slot> <id> [count] [nbt] §7- Add by position"
        )
        sender.send_message("§a/bd item remove <slot> §7- Remove at selected target")
        sender.send_message(
            "§a/bd item remove at <x> <y> <z> <slot> §7- Remove by position"
        )
        sender.send_message("§a/bd audit <start|stop> [x y z] §7- Record live diffs")
        sender.send_message("§a/bd audit history §7- Show recent audit sessions")
        sender.send_message(
            "§a/bd state set <property> <value> [x y z] §7- Mutate live block state"
        )

    def _require_bridge(
        self, sender: CommandSender, *capabilities: str, method: str | None = None
    ) -> Any | None:
        bridge = getattr(self, "live_bridge", None)
        if bridge is None:
            bridge = self._connect_bridge()
        if bridge is None:
            reason = getattr(self, "bridge_error", "native bridge is unavailable")
            sender.send_message(f"§cNative BlockData service unavailable: {reason}")
            return None

        if method and not hasattr(bridge, method):
            sender.send_message(
                f"§cInstalled BlockData bridge does not expose '{method}'. "
                "Install the matching native API package."
            )
            return None

        missing = [name for name in capabilities if not self.native_capabilities.get(name, False)]
        if missing:
            sender.send_message(
                "§cNative adapter does not support required capability: " + ", ".join(missing)
            )
            return None
        return bridge

    @staticmethod
    def _dimension_name(sender: CommandSender) -> str:
        location = getattr(sender, "location", None)
        dimension = getattr(location, "dimension", None)
        name = getattr(dimension, "name", None)
        return str(name) if name else "overworld"

    @staticmethod
    def _sender_key(sender: CommandSender) -> str:
        for attribute in ("unique_id", "xuid"):
            value = getattr(sender, attribute, None)
            if value is not None:
                return f"{attribute}:{value}"
        name = getattr(sender, "name", None)
        if name:
            return f"name:{str(name).casefold()}"
        return f"object:{id(sender)}"

    def _sender_position(
        self, sender: CommandSender
    ) -> tuple[str, int, int, int] | None:
        location = getattr(sender, "location", None)
        if location is None:
            sender.send_message("§cThis command needs a player location.")
            return None
        return (
            self._dimension_name(sender),
            math.floor(location.x),
            math.floor(location.y),
            math.floor(location.z),
        )

    def _parse_explicit_target(
        self, sender: CommandSender, args: list[str], usage: str
    ) -> tuple[str, int, int, int] | None:
        if len(args) != 3:
            sender.send_message(f"§cUsage: {usage}")
            return None
        try:
            x, y, z = (int(value) for value in args)
        except (TypeError, ValueError):
            sender.send_message("§cCoordinates must be three absolute integers: <x> <y> <z>.")
            return None
        return self._dimension_name(sender), x, y, z

    def _selected_target(
        self, sender: CommandSender
    ) -> tuple[str, int, int, int] | None:
        selected_targets = getattr(self, "selected_targets", {})
        target = selected_targets.get(self._sender_key(sender))
        if target is None:
            sender.send_message(
                "§cNo active container target. Run /bd locate or "
                "/bd inspect <x> <y> <z> first, or use an explicit-position form."
            )
        return target

    def _resolve_target(
        self, sender: CommandSender, args: list[str], usage: str
    ) -> tuple[str, int, int, int] | None:
        if args:
            return self._parse_explicit_target(sender, args, usage)
        return self._selected_target(sender)

    def _remember_target(
        self, sender: CommandSender, snapshot: dict[str, Any]
    ) -> tuple[str, int, int, int]:
        location = dict(snapshot["location"])
        target = (
            str(location.get("dimension") or self._dimension_name(sender)),
            int(location["x"]),
            int(location["y"]),
            int(location["z"]),
        )
        selected_targets = getattr(self, "selected_targets", None)
        if selected_targets is None:
            selected_targets = {}
            self.selected_targets = selected_targets
        selected_targets[self._sender_key(sender)] = target
        return target

    @classmethod
    def _looks_like_container_block(cls, snapshot: dict[str, Any]) -> bool:
        block_type = str(snapshot.get("type") or "").casefold()
        return block_type in cls._KNOWN_CONTAINER_BLOCKS or block_type.endswith(
            "_shulker_box"
        )

    @staticmethod
    def _inventory_entries(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        entity = snapshot.get("block_entity")
        if not isinstance(entity, dict):
            return []
        inventory = entity.get("inventory")
        if not isinstance(inventory, (list, tuple)):
            return []
        return [dict(slot) for slot in inventory if isinstance(slot, dict)]

    @classmethod
    def _container_inventory(
        cls, snapshot: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        entity = snapshot.get("block_entity")
        if not isinstance(entity, dict):
            return None
        inventory = cls._inventory_entries(snapshot)
        is_container = entity.get("is_container")
        if is_container is True:
            return inventory
        if is_container is False:
            return None
        # Compatibility with an older bridge shape: a positive declared size
        # or any returned inventory entries still proves container access.
        try:
            if int(entity.get("container_size", 0)) > 0:
                return inventory
        except (TypeError, ValueError):
            pass
        return inventory if inventory else None

    @staticmethod
    def _container_capacity(
        snapshot: dict[str, Any], inventory: list[dict[str, Any]]
    ) -> int:
        entity = snapshot.get("block_entity")
        if isinstance(entity, dict):
            try:
                capacity = int(entity.get("container_size", len(inventory)))
            except (TypeError, ValueError):
                capacity = len(inventory)
            if capacity >= 0:
                return capacity
        return len(inventory)

    @staticmethod
    def _block_entity_status(snapshot: dict[str, Any]) -> str:
        status = snapshot.get("block_entity_status")
        if status:
            return str(status)
        return "captured" if snapshot.get("block_entity") else "no_actor"

    @staticmethod
    def _is_empty_item(item: Any) -> bool:
        if item is None or item == {}:
            return True
        if not isinstance(item, dict):
            return False
        if item.get("empty") is True:
            return True
        item_id = item.get("Name", item.get("name", item.get("id")))
        if str(item_id or "").casefold() in {"air", "minecraft:air"}:
            return True
        count = item.get("Count", item.get("count"))
        return isinstance(count, int) and count <= 0

    @classmethod
    def _occupied_inventory(
        cls, inventory: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return [slot for slot in inventory if not cls._is_empty_item(slot.get("item"))]

    @staticmethod
    def _item_preview(slot: dict[str, Any]) -> str:
        item = dict(slot.get("item") or {})
        item_id = item.get("Name", item.get("name", item.get("id", "unknown")))
        count = item.get("Count", item.get("count", 1))
        custom_name = item.get("CustomName")
        tag = item.get("tag")
        if not custom_name and isinstance(tag, dict):
            display = tag.get("display")
            if isinstance(display, dict):
                custom_name = display.get("Name")
        label = f"slot {slot.get('slot', '?')}: {item_id} x{count}"
        return f"{label} ({custom_name})" if custom_name else label

    @classmethod
    def _canonical_nbt_preview(cls, nbt: Any) -> tuple[str, int, bool]:
        rendered = json.dumps(nbt or {}, default=str, separators=(",", ":"))
        total = len(rendered)
        limit = cls._MAX_CANONICAL_NBT_PREVIEW_CHARS
        if total <= limit:
            return rendered, total, False
        marker = f"... [TRUNCATED; {total} chars total]"
        prefix_length = max(0, limit - len(marker))
        return rendered[:prefix_length] + marker, total, True

    def _capture(
        self, sender: CommandSender, dimension: str, x: int, y: int, z: int
    ) -> dict[str, Any] | None:
        bridge = self._require_bridge(sender, method="capture")
        if bridge is None:
            return None
        try:
            snapshot = bridge.capture(self.server, dimension, x, y, z)
        except Exception as error:
            sender.send_message(f"§cNative capture failed: {error}")
            return None
        if snapshot is None:
            sender.send_message(f"§cNative service could not capture ({x}, {y}, {z}).")
            return None
        return dict(snapshot)

    def _handle_locate(self, sender: CommandSender, args: list[str]) -> bool:
        if len(args) > 1:
            sender.send_message("§cUsage: /bd locate [radius]")
            return True
        radius = 5
        if args:
            try:
                radius = max(0, min(int(args[0]), 12))
            except (TypeError, ValueError):
                sender.send_message("§cRadius must be an integer from 0 to 12.")
                return True

        bridge = self._require_bridge(
            sender, "block_entity_nbt", method="capture_region"
        )
        if bridge is None:
            return True
        center = self._sender_position(sender)
        if center is None:
            return True
        dimension, px, py, pz = center
        sender.send_message(
            f"§eScanning live blocks around ({px}, {py}, {pz}) within radius {radius}..."
        )
        try:
            snapshots = bridge.capture_region(
                self.server,
                dimension,
                px - radius,
                max(py - radius, -64),
                pz - radius,
                px + radius,
                min(py + radius, 319),
                pz + radius,
            )
        except Exception as error:
            sender.send_message(f"§cNative region capture failed: {error}")
            return True

        containers: list[dict[str, Any]] = []
        actor_capture_misses: list[dict[str, Any]] = []
        for raw_snapshot in snapshots:
            snapshot = dict(raw_snapshot)
            if self._container_inventory(snapshot) is not None:
                containers.append(snapshot)
            elif self._looks_like_container_block(snapshot):
                actor_capture_misses.append(snapshot)

        def distance_squared(snapshot: dict[str, Any]) -> int:
            location = dict(snapshot.get("location") or {})
            return (
                (int(location.get("x", px)) - px) ** 2
                + (int(location.get("y", py)) - py) ** 2
                + (int(location.get("z", pz)) - pz) ** 2
            )

        containers.sort(key=distance_squared)
        if containers:
            sender.send_message(f"§aFound {len(containers)} supported container actors:")
        else:
            sender.send_message(f"§cNo supported container actors found within radius {radius}.")

        for snapshot in containers[:10]:
            entity = dict(snapshot["block_entity"])
            location = dict(snapshot["location"])
            nbt = dict(entity.get("nbt") or {})
            inventory = self._container_inventory(snapshot) or []
            occupied = self._occupied_inventory(inventory)
            capacity = self._container_capacity(snapshot, inventory)
            previews = ", ".join(self._item_preview(slot) for slot in occupied[:3])
            if len(occupied) > 3:
                previews += f", +{len(occupied) - 3} more"
            sender.send_message(
                "  §7- Location: "
                f"§f({location['x']}, {location['y']}, {location['z']}) "
                f"§eType: §f{snapshot.get('type', 'unknown')} "
                f"§7Capacity: §b{capacity} §7Occupied: §b{len(occupied)} "
                f"§7Name: §f{nbt.get('CustomName', snapshot.get('type', 'unknown'))} "
                f"§7Items: §f{previews or 'empty'}"
            )

        if actor_capture_misses:
            sender.send_message(
                f"§cContainer actor/inventory capture missed for "
                f"{len(actor_capture_misses)} candidate block(s):"
            )
            for snapshot in actor_capture_misses[:5]:
                location = dict(snapshot.get("location") or {})
                sender.send_message(
                    "  §c- "
                    f"{snapshot.get('type', 'unknown')} at "
                    f"({location.get('x', '?')}, {location.get('y', '?')}, "
                    f"{location.get('z', '?')}) "
                    f"status={self._block_entity_status(snapshot)}"
                )

        if containers:
            dimension, x, y, z = self._remember_target(sender, containers[0])
            sender.send_message(
                f"§aSelected nearest container ({x}, {y}, {z}) in {dimension} "
                "as your active target."
            )
        return True

    def _handle_inspect(self, sender: CommandSender, args: list[str]) -> bool:
        explicit_target = bool(args)
        target = self._resolve_target(sender, args, "/bd inspect [<x> <y> <z>]")
        if target is None:
            return True
        dimension, x, y, z = target
        snapshot = self._capture(sender, dimension, x, y, z)
        if snapshot is None:
            return True

        sender.send_message(f"§e=== Live Block at ({x}, {y}, {z}) in {dimension} ===")
        sender.send_message(
            f"§7Block Type: §f{snapshot.get('type', 'unknown')} "
            f"§7(Runtime ID: §f{snapshot.get('runtime_id', 0)}§7)"
        )
        sender.send_message(f"§7Revision: §f{snapshot.get('revision', 0)}")
        states = dict(snapshot.get("states") or {})
        if states:
            sender.send_message("§7Block State Properties:")
            for name, value in states.items():
                sender.send_message(f"  §8- §f{name} = §b{value}")
        else:
            sender.send_message("§7Block State Properties: §oNone")

        raw_entity = snapshot.get("block_entity")
        if not raw_entity:
            if self._looks_like_container_block(snapshot):
                sender.send_message(
                    "§cContainer block detected, but its block actor/inventory "
                    "was not captured. "
                    f"Status: {self._block_entity_status(snapshot)}"
                )
            else:
                sender.send_message("§7Block Entity / NBT: §oNone (standard block)")
            return True
        entity = dict(raw_entity)
        sender.send_message(f"§7Block Entity: §a{entity.get('type', 'unknown')}")
        nbt_preview, nbt_characters, nbt_truncated = self._canonical_nbt_preview(
            entity.get("nbt") or {}
        )
        truncation = "; preview truncated" if nbt_truncated else ""
        sender.send_message(
            f"§7Canonical NBT ({nbt_characters} chars{truncation}): "
            f"§f{nbt_preview}"
        )
        inventory = self._container_inventory(snapshot)
        if inventory is None:
            sender.send_message("§7Container Inventory: §oNot a supported container")
            return True

        occupied = self._occupied_inventory(inventory)
        capacity = self._container_capacity(snapshot, inventory)
        sender.send_message(
            f"§7Container Capacity: §b{capacity} "
            f"§7Occupied: §b{len(occupied)}"
        )
        if occupied:
            sender.send_message("§7Occupied Contents:")
            for slot in occupied[:12]:
                sender.send_message(f"  §e- §f{self._item_preview(slot)}")
            if len(occupied) > 12:
                sender.send_message(f"  §7... and {len(occupied) - 12} more occupied slots")
        else:
            sender.send_message("§7Occupied Contents: §oEmpty")

        if explicit_target:
            self._remember_target(sender, snapshot)
            sender.send_message("§aSelected this container as your active target.")
        return True

    @staticmethod
    def _parse_non_negative_int(value: str) -> int | None:
        try:
            parsed = int(value)
        except ValueError:
            return None
        return parsed if parsed >= 0 else None

    @staticmethod
    def _empty_patch(snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            "location": dict(snapshot["location"]),
            "expected_revision": snapshot.get("revision"),
            "state_updates": {},
            "state_removals": [],
            "nbt_updates": {},
            "nbt_removals": [],
            "inventory_updates": {},
            "inventory_removals": [],
        }

    def _apply(
        self, sender: CommandSender, patch: dict[str, Any]
    ) -> dict[str, Any] | None:
        bridge = self._require_bridge(sender, method="apply")
        if bridge is None:
            return None
        try:
            return dict(bridge.apply(self.server, patch, "fail_if_changed"))
        except Exception as error:
            sender.send_message(f"§cNative apply failed: {error}")
            return None

    @staticmethod
    def _send_apply_failure(sender: CommandSender, result: dict[str, Any]) -> None:
        if result.get("status") == "conflict":
            sender.send_message(
                "§cThe block changed before the write was applied. Nothing was overwritten; "
                "inspect it and retry the command."
            )
            return
        sender.send_message(f"§cNative write failed: {result.get('message', 'unknown error')}")

    def _handle_item(self, sender: CommandSender, args: list[str]) -> bool:
        if not args or args[0].lower() not in {"add", "remove"}:
            sender.send_message(
                "§cUsage: /bd item add <slot> <item_id> [count] [nbt_json] or "
                "/bd item remove <slot> (add 'at <x> <y> <z>' for an explicit target)"
            )
            return True

        action = args[0].lower()
        explicit_target = len(args) > 1 and args[1].casefold() == "at"
        if action == "remove":
            expected_lengths = {6} if explicit_target else {2}
            usage = (
                "/bd item remove at <x> <y> <z> <slot>"
                if explicit_target
                else "/bd item remove <slot>"
            )
        else:
            expected_lengths = {7, 8, 9} if explicit_target else {3, 4, 5}
            usage = (
                "/bd item add at <x> <y> <z> <slot> <item_id> [count] [nbt_json]"
                if explicit_target
                else "/bd item add <slot> <item_id> [count] [nbt_json]"
            )
        if len(args) not in expected_lengths:
            sender.send_message(f"§cUsage: {usage}")
            return True

        if explicit_target:
            target = self._parse_explicit_target(sender, args[2:5], usage)
            slot_index = 5
            item_index = 6
        else:
            target = self._selected_target(sender)
            slot_index = 1
            item_index = 2
        if target is None:
            return True

        slot = self._parse_non_negative_int(args[slot_index])
        if slot is None:
            sender.send_message("§cSlot must be a non-negative integer.")
            return True

        item_id = ""
        count = 1
        nbt_data: dict[str, Any] = {}
        if action == "add":
            raw_item_id = args[item_index]
            item_id = raw_item_id if ":" in raw_item_id else f"minecraft:{raw_item_id}"
            option_args = args[item_index + 1 :]
            if option_args:
                count = self._parse_non_negative_int(option_args[0]) or 0
                if count < 1:
                    sender.send_message("§cItem count must be a positive integer.")
                    return True
            if len(option_args) == 2:
                try:
                    decoded = json.loads(option_args[1])
                except json.JSONDecodeError as error:
                    sender.send_message(f"§cFailed to parse NBT JSON: {error.msg}")
                    return True
                if not isinstance(decoded, dict):
                    sender.send_message("§cNBT JSON must be an object.")
                    return True
                nbt_data = decoded

        if self._require_bridge(sender, "inventory", method="apply") is None:
            return True
        dimension, x, y, z = target
        snapshot = self._capture(sender, dimension, x, y, z)
        if snapshot is None:
            return True
        inventory = self._container_inventory(snapshot)
        if inventory is None:
            if self._looks_like_container_block(snapshot):
                sender.send_message(
                    f"§cContainer at ({x}, {y}, {z}) is unavailable: "
                    f"{self._block_entity_status(snapshot)}."
                )
            else:
                sender.send_message(
                    f"§cBlock at ({x}, {y}, {z}) is not a supported container."
                )
            return True
        capacity = self._container_capacity(snapshot, inventory)
        if slot >= capacity:
            sender.send_message(
                f"§cSlot {slot} is outside this container's capacity of {capacity}."
            )
            return True

        patch = self._empty_patch(snapshot)
        if action == "remove":
            patch["inventory_removals"] = [slot]
            result = self._apply(sender, patch)
            if result is not None:
                if result.get("ok"):
                    sender.send_message(f"§aCleared live item in slot {slot} at ({x}, {y}, {z}).")
                else:
                    self._send_apply_failure(sender, result)
            return True

        patch["inventory_updates"] = {
            slot: {"id": item_id, "count": count, "tag": nbt_data}
        }
        result = self._apply(sender, patch)
        if result is not None:
            if result.get("ok"):
                sender.send_message(
                    f"§aAdded {count}x {item_id} to live slot {slot} "
                    f"at ({x}, {y}, {z})."
                )
            else:
                self._send_apply_failure(sender, result)
        return True

    @classmethod
    def _inventory(cls, snapshot: dict[str, Any]) -> dict[int, Any]:
        return {
            int(slot["slot"]): slot.get("item")
            for slot in cls._inventory_entries(snapshot)
            if "slot" in slot and not cls._is_empty_item(slot.get("item"))
        }

    @classmethod
    def _diff_snapshots(
        cls, before: dict[str, Any], after: dict[str, Any]
    ) -> dict[str, Any]:
        left, right = cls._inventory(before), cls._inventory(after)
        changes = []
        for slot in sorted(set(left) | set(right)):
            old, new = left.get(slot), right.get(slot)
            if old == new:
                continue
            kind = "added" if slot not in left else "removed" if slot not in right else "changed"
            changes.append({"slot": slot, "kind": kind, "before": old, "after": new})
        before_entity, after_entity = before.get("block_entity"), after.get("block_entity")
        return {
            "location": dict(after["location"]),
            "block_changed": (before.get("type"), before.get("runtime_id"), before.get("states"))
            != (after.get("type"), after.get("runtime_id"), after.get("states")),
            "actor_nbt_changed": (before_entity or {}).get("nbt")
            != (after_entity or {}).get("nbt"),
            "inventory_changes": changes,
        }

    def _handle_audit(self, sender: CommandSender, args: list[str]) -> bool:
        if not args or args[0].lower() not in {"start", "stop", "history"}:
            sender.send_message(
                "§cUsage: /bd audit <start|stop> [x y z] or /bd audit history"
            )
            return True
        operation = args[0].lower()
        if operation == "history":
            if len(args) != 1:
                sender.send_message("§cUsage: /bd audit history")
                return True
            audit_logs = getattr(self, "audit_logs", [])
            sender.send_message(f"§e=== Live Audit History ({len(audit_logs)} sessions) ===")
            for index, delta in enumerate(audit_logs[-5:], 1):
                location = delta["location"]
                sender.send_message(
                    f" §7#{index}: ({location['x']}, {location['y']}, {location['z']}) "
                    f"changes={len(delta['inventory_changes'])}"
                )
            return True

        if len(args) not in {1, 4}:
            sender.send_message("§cUsage: /bd audit <start|stop> [x y z]")
            return True
        target = self._resolve_target(
            sender, args[1:], "/bd audit <start|stop> [<x> <y> <z>]"
        )
        if target is None:
            return True
        dimension, x, y, z = target
        key = (self._sender_key(sender), dimension, x, y, z)
        audit_baselines = getattr(self, "audit_baselines", None)
        if audit_baselines is None:
            audit_baselines = {}
            self.audit_baselines = audit_baselines
        if operation == "start":
            snapshot = self._capture(sender, dimension, x, y, z)
            if snapshot is not None:
                audit_baselines[key] = snapshot
                sender.send_message(f"§aStarted live audit for ({x}, {y}, {z}).")
            return True

        baseline = audit_baselines.get(key)
        if baseline is None:
            sender.send_message("§cNo active audit baseline found for this block.")
            return True
        current = self._capture(sender, dimension, x, y, z)
        if current is None:
            return True
        audit_baselines.pop(key, None)
        delta = self._diff_snapshots(baseline, current)
        audit_logs = getattr(self, "audit_logs", None)
        if audit_logs is None:
            audit_logs = []
            self.audit_logs = audit_logs
        audit_logs.append(delta)
        sender.send_message(f"§e=== Live Audit Report for ({x}, {y}, {z}) ===")
        sender.send_message(
            f"§7Block Changed: §f{delta['block_changed']} "
            f"§7NBT Changed: §f{delta['actor_nbt_changed']}"
        )
        sender.send_message(f"§7Inventory Changes: §b{len(delta['inventory_changes'])}")
        for change in delta["inventory_changes"]:
            sender.send_message(
                f"  §e[{change['kind']}] §fSlot {change['slot']}: "
                f"{json.dumps(change['before'], default=str)} -> "
                f"{json.dumps(change['after'], default=str)}"
            )
        return True

    @staticmethod
    def _parse_state_value(value: str) -> bool | int | str:
        lowered = value.casefold()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        try:
            return int(value)
        except ValueError:
            return value

    def _handle_state(self, sender: CommandSender, args: list[str]) -> bool:
        if len(args) not in {3, 6} or args[0].lower() != "set":
            sender.send_message(
                "§cUsage: /bd state set <property_name> <value> [x y z]"
            )
            return True
        target = self._resolve_target(
            sender,
            args[3:],
            "/bd state set <property_name> <value> [<x> <y> <z>]",
        )
        if target is None:
            return True
        if self._require_bridge(sender, "block_writes", method="apply") is None:
            return True

        dimension, x, y, z = target
        snapshot = self._capture(sender, dimension, x, y, z)
        if snapshot is None:
            return True
        property_name = args[1]
        property_value = self._parse_state_value(args[2])
        patch = self._empty_patch(snapshot)
        patch["state_updates"] = {property_name: property_value}
        result = self._apply(sender, patch)
        if result is not None:
            if result.get("ok"):
                sender.send_message(
                    f"§aSet live '{property_name}' to '{property_value}' at ({x}, {y}, {z}). "
                    f"New revision: {result.get('resulting_revision', 0)}"
                )
            else:
                self._send_apply_failure(sender, result)
        return True
