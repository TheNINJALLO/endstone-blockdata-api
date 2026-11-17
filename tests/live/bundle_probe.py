"""Primary-thread fixture embedded in the disposable acceptance-test wheel."""
from pathlib import Path
import json
import traceback

from endstone.plugin import Plugin

RESULT = Path(__RESULT_PATH__)
MODE = Path(__MODE_PATH__)
LOCATION = {"dimension": "Overworld", "x": 0, "y": 290, "z": 0}
NAME = "Endstone 0.11.16 native qualification"


class Probe(Plugin):
    api_version = "0.11"
    depend = ["blockdata_api"]

    def on_enable(self):
        self.attempts = 0
        self.server.scheduler.run_task(self, self.prepare, delay=40)

    def prepare(self):
        self.server.dispatch_command(self.server.command_sender,
                                     "tickingarea add circle 8 0 8 1 blockdata_probe true")
        self.server.scheduler.run_task(self, self.check, delay=40)

    def check(self):
        from endstone_blockdata_inspector import _endstone_blockdata_live as bridge
        try:
            self.attempts += 1
            snapshot = bridge.capture(self.server, **LOCATION)
            if snapshot is None:
                if self.attempts >= 30:
                    raise RuntimeError("Disposable probe chunk did not load")
                self.server.scheduler.run_task(self, self.check, delay=20)
                return
            native = self.server.plugin_manager.get_plugin("blockdata_api")
            assert native._get_description().version == bridge.__version__ == "0.6.10"
            assert bridge.available(self.server)
            from bundle_probe_adapter import BlockDataAdapter
            antigrief = BlockDataAdapter()
            assert antigrief.connect(self.server), antigrief.error
            try:
                bridge._roundtrip_nbt(bridge._NbtByte(128))
            except ValueError:
                pass
            else:
                raise AssertionError("Invalid byte NBT was accepted")
            checks = {"service_and_bridge": True, "dependent_antigrief_adapter": True,
                      "invalid_nbt_rejected": True}
            if MODE.read_text() == "write":
                stale_revision = snapshot["revision"]
                result = bridge.apply(self.server, {"location": LOCATION,
                                      "expected_revision": snapshot["revision"],
                                      "replacement_type": "minecraft:barrel"})
                assert result["ok"], result
                snapshot = bridge.capture(self.server, **LOCATION)
                assert snapshot["type"] == "minecraft:barrel", snapshot
                checks["block_write"] = True
                result = bridge.apply(self.server, {"location": LOCATION,
                                      "expected_revision": snapshot["revision"],
                                      "nbt_updates": {"CustomName": NAME, "HasCustomName": bridge._NbtByte(1)}})
                assert result["ok"], result
                snapshot = bridge.capture(self.server, **LOCATION)
                assert snapshot["block_entity"]["nbt"]["CustomName"] == NAME, snapshot
                checks["canonical_actor_nbt_write"] = True
                item = {"Name": "minecraft:diamond", "Count": bridge._NbtByte(4),
                        "Damage": bridge._NbtShort(0), "tag": {"display": {"Name": "Verified native item"}}}
                bundle = {"Name": "minecraft:bundle", "Count": bridge._NbtByte(1), "Damage": bridge._NbtShort(0),
                          "tag": {"storage_item_component_content": [
                              {"Name": "minecraft:diamond", "Count": bridge._NbtByte(2),
                               "Damage": bridge._NbtShort(0), "Slot": bridge._NbtByte(0)}]}}
                result = bridge.apply(self.server, {"location": LOCATION,
                                      "expected_revision": snapshot["revision"],
                                      "inventory_updates": {0: item, 1: bundle}})
                assert result["ok"], result
                checks["native_container_and_bundle_write"] = True
                conflict = bridge.apply(self.server, {"location": LOCATION,
                                        "expected_revision": stale_revision,
                                        "nbt_updates": {"CustomName": "Must not overwrite"}})
                assert not conflict["ok"], conflict
                checks["stale_snapshot_rejected"] = True
            snapshot = bridge.capture(self.server, **LOCATION)
            actor = snapshot["block_entity"]
            assert snapshot["type"] == "minecraft:barrel"
            assert actor["canonical"] and actor["nbt"]["CustomName"] == NAME, actor
            inventory = {entry["slot"]: entry["item"] for entry in actor["inventory"]}
            assert inventory[0]["Name"] == "minecraft:diamond" and inventory[0]["Count"] == 4, inventory
            assert inventory[0]["tag"]["display"]["Name"] == "Verified native item", inventory
            contents = inventory[1]["tag"]["storage_item_component_content"]
            assert len(contents) == 1 and contents[0]["Name"] == "minecraft:diamond" and contents[0]["Count"] == 2, contents
            checks.update(container_item_and_user_nbt=True, native_bundle_roundtrip=True)
            report = {"passed": True, "mode": MODE.read_text(), "checks": checks,
                      "native_version": bridge.__version__, "capabilities": bridge.capabilities(self.server)}
        except Exception:
            report = {"passed": False, "error": traceback.format_exc()}
        RESULT.write_text(json.dumps(report, indent=2), encoding="utf-8")
