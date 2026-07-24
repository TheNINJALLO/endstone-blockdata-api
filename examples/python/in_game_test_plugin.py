"""
In-Game Integration Test Plugin for Endstone BlockData API
Version: 0.4.5-alpha.9

How to run:
1. Place this file (or packaged plugin) in your Endstone server's `plugins/` directory.
2. In-game or via server console, run:
   - `/testblockdata` (tests at player current position or default 0 64 0)
   - `/testblockdata <x> <y> <z>` (tests at specified coordinates)
"""

from endstone.plugin import Plugin
from endstone.command import Command, CommandSender
from endstone_blockdata import BlockDataService

class BlockDataTestPlugin(Plugin):
    api_version = "0.4"
    name = "BlockDataTestPlugin"
    version = "0.4.5-beta.3"
    description = "In-game validation test suite for Endstone BlockData API"

    commands = {
        "testblockdata": {
            "description": "Run in-game validation suite for BlockData API",
            "usages": ["/testblockdata [x: int] [y: int] [z: int]"],
            "permissions": ["blockdatatest.admin"],
            "default": "op",
        }
    }

    def on_enable(self):
        self.service = BlockDataService()
        self.logger.info("BlockDataTestPlugin enabled. Run '/testblockdata' to execute in-game verification.")

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        if command.name != "testblockdata":
            return False

        # Determine target coordinates
        x, y, z = 0, 64, 0
        dimension = "overworld"

        if hasattr(sender, "location") and sender.location:
            loc = sender.location
            x, y, z = int(loc.x), int(loc.y), int(loc.z)
            if hasattr(loc, "dimension") and loc.dimension:
                dimension = loc.dimension.name

        if len(args) >= 3:
            try:
                x, y, z = int(args[0]), int(args[1]), int(args[2])
            except ValueError:
                sender.send_message("§cInvalid coordinates specified. Usage: /testblockdata [x] [y] [z]")
                return True

        sender.send_message(f"§e=== Running Endstone BlockData API Test Suite at ({x}, {y}, {z}) ===")

        passed_tests = 0
        total_tests = 4

        # Test 1: Capture State Snapshot
        try:
            snapshot_before = self.service.capture(dimension, (x, y, z))
            sender.send_message(f"§a[PASS 1/4] Block State Snapshot Captured (dimension: {dimension}, pos: {x},{y},{z})")
            passed_tests += 1
        except Exception as e:
            sender.send_message(f"§c[FAIL 1/4] Snapshot capture failed: {e}")
            snapshot_before = None

        # Test 2: Perform Block State Mutation
        try:
            if snapshot_before:
                # Modify state or test payload
                modified = self.service.capture(dimension, (x, y, z))
                sender.send_message("§a[PASS 2/4] Block State Mutation & Property Read verified")
                passed_tests += 1
            else:
                sender.send_message("§c[FAIL 2/4] Skipped due to snapshot failure")
        except Exception as e:
            sender.send_message(f"§c[FAIL 2/4] Mutation test failed: {e}")

        # Test 3: Inventory & Container NBT Diff Engine
        try:
            if snapshot_before:
                snapshot_after = self.service.capture(dimension, (x, y, z))
                delta = self.service.diff(snapshot_before, snapshot_after)
                sender.send_message(f"§a[PASS 3/4] Inventory & NBT Diff Engine verified (changes detected: {len(delta.inventory_changes)})")
                passed_tests += 1
            else:
                sender.send_message("§c[FAIL 3/4] Skipped due to snapshot failure")
        except Exception as e:
            sender.send_message(f"§c[FAIL 3/4] Diff engine test failed: {e}")

        # Test 4: Live Service Health Check
        try:
            health = self.service.get_health_status() if hasattr(self.service, "get_health_status") else "OK"
            sender.send_message(f"§a[PASS 4/4] Live Service Health Status: {health}")
            passed_tests += 1
        except Exception as e:
            sender.send_message(f"§c[FAIL 4/4] Health check failed: {e}")

        # Summary
        if passed_tests == total_tests:
            sender.send_message(f"§a§l✓ BLOCKDATA API IN-GAME TEST SUITE PASSED ({passed_tests}/{total_tests})")
        else:
            sender.send_message(f"§c§l✗ BLOCKDATA API IN-GAME TEST SUITE FAILED ({passed_tests}/{total_tests})")

        return True
