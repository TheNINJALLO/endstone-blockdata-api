"""Endstone BlockData live-service command test plugin."""

from __future__ import annotations

import json
from typing import Any

from endstone.command import Command, CommandSender
from endstone.plugin import Plugin

from ._bridge_loader import import_live_bridge


class BlockDataInspectorPlugin(Plugin):
    """Exercise the native BlockData service from in-game commands."""

    api_version = "0.11"
    version = "0.4.5-beta.31"
    description = "Interactive in-game container, NBT, and block-state test suite"
    depend = ["blockdata_api"]

    commands = {
        "bd": {
            "description": "BlockData inspector and container NBT test suite",
            "usages": [
                "/bd",
                "/bd (locate)<action: BlockDataLocateAction> [radius: int]",
                "/bd (inspect)<action: BlockDataInspectAction> [position: block_pos]",
                (
                    "/bd (item)<action: BlockDataItemAction> "
                    "(add)<operation: BlockDataItemAddOperation> <slot: int> "
                    "<item_id: str> [count: int] [nbt: json]"
                ),
                (
                    "/bd (item)<action: BlockDataItemAction> "
                    "(remove)<operation: BlockDataItemRemoveOperation> <slot: int>"
                ),
                (
                    "/bd (audit)<action: BlockDataAuditAction> "
                    "(start|stop)<operation: BlockDataAuditToggle> [position: block_pos]"
                ),
                (
                    "/bd (audit)<action: BlockDataAuditAction> "
                    "(history)<operation: BlockDataAuditHistory>"
                ),
                (
                    "/bd (state)<action: BlockDataStateAction> "
                    "(set)<operation: BlockDataStateSet> <property: str> <value: str> "
                    "[position: block_pos]"
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

    def on_enable(self) -> None:
        self.audit_baselines: dict[tuple[str, int, int, int], dict[str, Any]] = {}
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
                self.bridge_error = "endstone:blockdata native service is not registered"
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
        sender.send_message("§e=== BlockData Inspector Test Plugin (v0.4.5-beta.31) ===")
        sender.send_message("§a/bd locate [radius]                 §7- Locate nearby containers")
        sender.send_message("§a/bd inspect [x y z]                §7- Inspect live block state and NBT")
        sender.send_message("§a/bd item add <slot> <id> [count] [nbt] §7- Add a container item")
        sender.send_message("§a/bd item remove <slot>             §7- Remove a container item")
        sender.send_message("§a/bd audit <start|stop|history> [x y z] §7- Record live inventory diffs")
        sender.send_message("§a/bd state set <property> <value> [x y z] §7- Mutate live block state")

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

    def _get_target_pos(
        self, sender: CommandSender, args: list[str]
    ) -> tuple[str, int, int, int]:
        location = getattr(sender, "location", None)
        if location is None:
            x, y, z = 0, 64, 0
        else:
            x, y, z = int(location.x), int(location.y), int(location.z)
        if len(args) >= 3:
            try:
                x, y, z = int(args[0]), int(args[1]), int(args[2])
            except ValueError:
                pass
        return self._dimension_name(sender), x, y, z

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
        radius = 5
        if args:
            try:
                radius = max(0, min(int(args[0]), 12))
            except ValueError:
                sender.send_message("§cRadius must be an integer from 0 to 12.")
                return True

        bridge = self._require_bridge(
            sender, "block_entity_nbt", method="capture_region"
        )
        if bridge is None:
            return True
        dimension, px, py, pz = self._get_target_pos(sender, [])
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

        containers = [dict(snapshot) for snapshot in snapshots if snapshot.get("block_entity")]
        if not containers:
            sender.send_message(f"§cNo container block entities found within radius {radius}.")
            return True

        sender.send_message(f"§aFound {len(containers)} container block entities:")
        for snapshot in containers[:10]:
            entity = dict(snapshot["block_entity"])
            location = dict(snapshot["location"])
            nbt = dict(entity.get("nbt") or {})
            sender.send_message(
                "  §7- Location: "
                f"§f({location['x']}, {location['y']}, {location['z']}) "
                f"§eType: §f{snapshot.get('type', 'unknown')} "
                f"§7Slots: §b{len(entity.get('inventory') or [])} "
                f"§7Name: §f{nbt.get('CustomName', snapshot.get('type', 'unknown'))}"
            )
        return True

    def _handle_inspect(self, sender: CommandSender, args: list[str]) -> bool:
        dimension, x, y, z = self._get_target_pos(sender, args)
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
            sender.send_message("§7Block Entity / NBT: §oNone (standard block)")
            return True
        entity = dict(raw_entity)
        sender.send_message(f"§7Block Entity: §a{entity.get('type', 'unknown')}")
        sender.send_message(
            f"§7Canonical NBT: §f{json.dumps(entity.get('nbt') or {}, default=str)}"
        )
        inventory = list(entity.get("inventory") or [])
        sender.send_message(f"§7Container Inventory: §b{len(inventory)} items")
        for slot in inventory:
            sender.send_message(
                f"  §eSlot {slot.get('slot', '?')}: "
                f"§f{json.dumps(slot.get('item'), default=str)}"
            )
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
        if len(args) < 2 or args[0].lower() not in {"add", "remove"}:
            sender.send_message(
                "§cUsage: /bd item <add|remove> <slot> [item_id] [count] [nbt_json]"
            )
            return True
        if self._require_bridge(sender, "inventory", method="apply") is None:
            return True

        action = args[0].lower()
        slot = self._parse_non_negative_int(args[1])
        if slot is None:
            sender.send_message("§cSlot must be a non-negative integer.")
            return True
        dimension, x, y, z = self._get_target_pos(sender, [])
        snapshot = self._capture(sender, dimension, x, y, z)
        if snapshot is None:
            return True
        if not snapshot.get("block_entity"):
            sender.send_message(f"§cBlock at ({x}, {y}, {z}) is not a container.")
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

        if len(args) < 3:
            sender.send_message("§cUsage: /bd item add <slot> <item_id> [count] [nbt_json]")
            return True
        item_id = args[2] if ":" in args[2] else f"minecraft:{args[2]}"
        count = 1
        if len(args) > 3:
            count = self._parse_non_negative_int(args[3]) or 0
            if count < 1:
                sender.send_message("§cItem count must be a positive integer.")
                return True

        nbt_data: dict[str, Any] = {}
        if len(args) > 4:
            try:
                decoded = json.loads(" ".join(args[4:]))
            except json.JSONDecodeError as error:
                sender.send_message(f"§cFailed to parse NBT JSON: {error.msg}")
                return True
            if not isinstance(decoded, dict):
                sender.send_message("§cNBT JSON must be an object.")
                return True
            nbt_data = decoded

        patch["inventory_updates"] = {
            slot: {"id": item_id, "count": count, "tag": nbt_data}
        }
        result = self._apply(sender, patch)
        if result is not None:
            if result.get("ok"):
                sender.send_message(f"§aAdded {count}x {item_id} to live slot {slot}.")
            else:
                self._send_apply_failure(sender, result)
        return True

    @staticmethod
    def _inventory(snapshot: dict[str, Any]) -> dict[int, Any]:
        entity = snapshot.get("block_entity") or {}
        return {
            int(slot["slot"]): slot.get("item")
            for slot in entity.get("inventory", [])
            if "slot" in slot
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
            sender.send_message("§cUsage: /bd audit <start|stop|history> [x] [y] [z]")
            return True
        operation = args[0].lower()
        if operation == "history":
            sender.send_message(f"§e=== Live Audit History ({len(self.audit_logs)} sessions) ===")
            for index, delta in enumerate(self.audit_logs[-5:], 1):
                location = delta["location"]
                sender.send_message(
                    f" §7#{index}: ({location['x']}, {location['y']}, {location['z']}) "
                    f"changes={len(delta['inventory_changes'])}"
                )
            return True

        dimension, x, y, z = self._get_target_pos(sender, args[1:])
        key = (dimension, x, y, z)
        if operation == "start":
            snapshot = self._capture(sender, dimension, x, y, z)
            if snapshot is not None:
                self.audit_baselines[key] = snapshot
                sender.send_message(f"§aStarted live audit for ({x}, {y}, {z}).")
            return True

        baseline = self.audit_baselines.get(key)
        if baseline is None:
            sender.send_message("§cNo active audit baseline found for this block.")
            return True
        current = self._capture(sender, dimension, x, y, z)
        if current is None:
            return True
        self.audit_baselines.pop(key, None)
        delta = self._diff_snapshots(baseline, current)
        self.audit_logs.append(delta)
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
        if len(args) < 3 or args[0].lower() != "set":
            sender.send_message(
                "§cUsage: /bd state set <property_name> <value> [x] [y] [z]"
            )
            return True
        if self._require_bridge(sender, "block_writes", method="apply") is None:
            return True

        dimension, x, y, z = self._get_target_pos(sender, args[3:])
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
