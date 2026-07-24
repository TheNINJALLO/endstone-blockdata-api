"""
BlockDataInspectorPlugin - Advanced Container & NBT In-Game Test Plugin
Endstone API Version: 0.4
Depends on: endstone_blockdata (v0.4.5-alpha.9)
"""

import json
from endstone.plugin import Plugin
from endstone.command import Command, CommandSender
from endstone_blockdata import (
    BlockDataService,
    ContainerView,
    BlockPatch,
    ConflictPolicy,
    BlockLocation,
    InventoryChangeKind,
)

class BlockDataInspectorPlugin(Plugin):
    api_version = "0.4"
    name = "BlockDataInspectorPlugin"
    version = "0.4.5-beta.2"
    description = "Interactive In-Game Container, NBT, and Block State Test Suite"

    commands = {
        "bd": {
            "description": "BlockData Inspector & Container NBT Test Suite",
            "usages": ["/bd <locate|inspect|item|audit|state> [args...]"],
            "permissions": ["bd.admin"],
            "default": "op",
        }
    }

    def on_enable(self):
        self.service = BlockDataService()
        self.audit_active = False
        self.audit_baseline = {}
        self.audit_logs = []
        self.logger.info("BlockDataInspectorPlugin enabled. Type '/bd' in-game or console for help.")

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        if not args:
            self._send_help(sender)
            return True

        subcmd = args[0].lower()

        if subcmd == "locate":
            return self._handle_locate(sender, args[1:])
        elif subcmd == "inspect":
            return self._handle_inspect(sender, args[1:])
        elif subcmd == "item":
            return self._handle_item(sender, args[1:])
        elif subcmd == "audit":
            return self._handle_audit(sender, args[1:])
        elif subcmd == "state":
            return self._handle_state(sender, args[1:])
        else:
            self._send_help(sender)
            return True

    def _send_help(self, sender: CommandSender):
        sender.send_message("§e=== BlockData Inspector Test Plugin (v0.4.5-alpha.9) ===")
        sender.send_message("§a/bd locate [radius]              §7- Locate nearby container blocks")
        sender.send_message("§a/bd inspect [x] [y] [z]           §7- Inspect block state & NBT container slots")
        sender.send_message("§a/bd item add <slot> <id> [cnt] [nbt] §7- Add item with NBT data to slot")
        sender.send_message("§a/bd item remove <slot>            §7- Remove item from slot via NBT patch")
        sender.send_message("§a/bd audit <start|stop|history>    §7- Container audit & inventory diff recorder")
        sender.send_message("§a/bd state set <prop> <val>        §7- Mutate block state properties")

    def _get_target_pos(self, sender: CommandSender, args: list[str]) -> tuple[str, int, int, int]:
        dim = "overworld"
        x, y, z = 0, 64, 0
        if hasattr(sender, "location") and sender.location:
            loc = sender.location
            x, y, z = int(loc.x), int(loc.y), int(loc.z)
            if hasattr(loc, "dimension") and loc.dimension:
                dim = loc.dimension.name

        if len(args) >= 3:
            try:
                x, y, z = int(args[0]), int(args[1]), int(args[2])
            except ValueError:
                pass
        return dim, x, y, z

    def _handle_locate(self, sender: CommandSender, args: list[str]) -> bool:
        radius = 5
        if args and args[0].isdigit():
            radius = min(int(args[0]), 25)

        dim, px, py, pz = self._get_target_pos(sender, [])
        sender.send_message(f"§eScanning for containers around ({px}, {py}, {pz}) within radius {radius}...")

        min_pos = (px - radius, max(py - radius, -64), pz - radius)
        max_pos = (px + radius, min(py + radius, 319), pz + radius)

        snapshots = self.service.capture_region(dim, min_pos, max_pos)
        containers_found = []

        for s in snapshots:
            if s.block_entity is not None:
                slot_cnt = len(s.block_entity.inventory)
                containers_found.append((s.location, s.type, slot_cnt, s.block_entity.nbt))

        if not containers_found:
            sender.send_message(f"§cNo container block entities found within radius {radius}.")
        else:
            sender.send_message(f"§aFound {len(containers_found)} container block entities:")
            for loc, btype, slots, nbt in containers_found[:10]:
                custom_name = nbt.get("CustomName", btype)
                sender.send_message(f"  §7- Location: §f({loc.x}, {loc.y}, {loc.z}) §eType: §f{btype} §7Slots: §b{slots} §7Name: §f{custom_name}")

        return True

    def _handle_inspect(self, sender: CommandSender, args: list[str]) -> bool:
        dim, x, y, z = self._get_target_pos(sender, args)
        sender.send_message(f"§e=== Inspecting Block at ({x}, {y}, {z}) in {dim} ===")

        snap = self.service.capture(dim, (x, y, z))
        sender.send_message(f"§7Block Type: §f{snap.type} §7(Runtime ID: §f{snap.runtime_id}§7)")
        sender.send_message(f"§7Revision: §f{snap.revision}")

        if snap.states:
            sender.send_message("§7Block State Properties:")
            for k, v in snap.states.items():
                sender.send_message(f"  §8- §f{k} = §b{v}")
        else:
            sender.send_message("§7Block State Properties: §oNone")

        if snap.block_entity:
            view = ContainerView(snap)
            sender.send_message(f"§7Block Entity: §a{snap.block_entity.type_name}")
            sender.send_message(f"§7Canonical NBT Tags: §f{json.dumps(view.nbt)}")
            inventory = snap.block_entity.inventory
            if inventory:
                sender.send_message(f"§7Container Inventory Slots ({len(inventory)} items):")
                for slot in inventory:
                    sender.send_message(f"  §eSlot {slot.slot}: §f{json.dumps(slot.item)}")
            else:
                sender.send_message("§7Container Inventory Slots: §oEmpty")
        else:
            sender.send_message("§7Block Entity / NBT: §oNone (Standard Block)")

        return True

    def _handle_item(self, sender: CommandSender, args: list[str]) -> bool:
        if not args or args[0].lower() not in ("add", "remove"):
            sender.send_message("§cUsage: /bd item <add|remove> <slot> [item_id] [count] [nbt_json]")
            return True

        action = args[0].lower()
        if len(args) < 2 or not args[1].isdigit():
            sender.send_message("§cSpecify a valid slot index. Example: /bd item add 0 diamond 64")
            return True

        slot = int(args[1])
        dim, x, y, z = self._get_target_pos(sender, args[5:] if len(args) >= 8 else [])

        snap = self.service.capture(dim, (x, y, z))
        if snap.block_entity is None:
            sender.send_message(f"§cBlock at ({x}, {y}, {z}) is not a container block entity!")
            return True

        view = ContainerView(snap)

        if action == "add":
            item_id = args[2] if len(args) > 2 else "minecraft:diamond"
            count = int(args[3]) if len(args) > 3 and args[3].isdigit() else 1
            nbt_data = {}
            if len(args) > 4:
                try:
                    nbt_data = json.loads(" ".join(args[4:]))
                except Exception as e:
                    sender.send_message(f"§cFailed to parse NBT JSON: {e}")
                    return True

            item_payload = {
                "id": item_id,
                "count": count,
                "tag": nbt_data
            }

            patch = view.patch_item(slot, item_payload)
            res = self.service.apply(patch, ConflictPolicy.FORCE)
            if res.success:
                sender.send_message(f"§aAdded item to slot {slot} at ({x}, {y}, {z}): §f{count}x {item_id} NBT: {nbt_data}")
            else:
                sender.send_message(f"§cFailed to patch item: {res.message}")

        elif action == "remove":
            patch = view.clear_item(slot)
            res = self.service.apply(patch, ConflictPolicy.FORCE)
            if res.success:
                sender.send_message(f"§aCleared item at slot {slot} at ({x}, {y}, {z}).")
            else:
                sender.send_message(f"§cFailed to clear item: {res.message}")

        return True

    def _handle_audit(self, sender: CommandSender, args: list[str]) -> bool:
        if not args:
            sender.send_message("§cUsage: /bd audit <start|stop|history>")
            return True

        sub = args[0].lower()
        dim, x, y, z = self._get_target_pos(sender, args[1:])

        if sub == "start":
            self.audit_active = True
            snap = self.service.capture(dim, (x, y, z))
            self.audit_baseline[(dim, x, y, z)] = snap
            sender.send_message(f"§aStarted container audit recorder for block at ({x}, {y}, {z}).")

        elif sub == "stop":
            if not self.audit_active or (dim, x, y, z) not in self.audit_baseline:
                sender.send_message("§cNo active audit baseline found for this block.")
                return True

            baseline = self.audit_baseline.pop((dim, x, y, z))
            current = self.service.capture(dim, (x, y, z))
            delta = self.service.diff(baseline, current)

            sender.send_message(f"§e=== Container Transaction Audit Report for ({x}, {y}, {z}) ===")
            sender.send_message(f"§7Block Changed: §f{delta.block_changed} §7NBT Changed: §f{delta.actor_nbt_changed}")
            sender.send_message(f"§7Inventory Change Count: §b{len(delta.inventory_changes)}")

            for change in delta.inventory_changes:
                kind_str = change.kind.name if hasattr(change.kind, "name") else str(change.kind)
                before_str = json.dumps(change.before) if change.before else "None"
                after_str = json.dumps(change.after) if change.after else "None"
                sender.send_message(f"  §e[{kind_str}] §fSlot {change.slot}: Before={before_str} -> After={after_str}")

            self.audit_logs.append(delta)
            self.audit_active = False

        elif sub == "history":
            sender.send_message(f"§e=== Audit History ({len(self.audit_logs)} sessions recorded) ===")
            for idx, log in enumerate(self.audit_logs[-5:], 1):
                sender.send_message(f" §7#{idx}: Pos ({log.location.x},{log.location.y},{log.location.z}) Changes: {len(log.inventory_changes)}")

        return True

    def _handle_state(self, sender: CommandSender, args: list[str]) -> bool:
        if len(args) < 2:
            sender.send_message("§cUsage: /bd state set <property_name> <value> [x] [y] [z]")
            return True

        prop_name = args[1]
        prop_val = args[2] if len(args) >= 3 else "true"

        dim, x, y, z = self._get_target_pos(sender, args[3:] if len(args) >= 6 else [])

        snap = self.service.capture(dim, (x, y, z))
        patch = BlockPatch(snap.location, snap.revision, state_updates={prop_name: prop_val})

        res = self.service.apply(patch, ConflictPolicy.FORCE)
        if res.success:
            sender.send_message(f"§aMutated block property '{prop_name}' to '{prop_val}' at ({x}, {y}, {z}). New Revision: {res.new_revision}")
        else:
            sender.send_message(f"§cFailed to mutate block state: {res.message}")

        return True
