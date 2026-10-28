from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] if Path(__file__).parent.name == "python" else Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_prepared_hooks", ROOT / "scripts/verify_prepared_hooks.py")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class TestPreparedHooks(unittest.TestCase):
    def fixture(self, folder):
        data = b"exact executable fixture"
        executable = folder / "bedrock_server"
        executable.write_bytes(data)
        manifest = {
            "bds_package": "1.26.60.6", "platform": "linux-x64",
            "executable": {"sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)},
            "sites": [{"status": "mapped-offline", "uses": ["hook"], "previous_address": "0x1", "file_offset": 6, "bytes": b"executable".hex()}],
            "qualification_required": ["matching SDK and runtime"],
        }
        return manifest, executable

    def test_identity_and_instruction_bytes_are_both_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, executable = self.fixture(Path(directory))
            self.assertEqual(VERIFY.verify(manifest, executable)["sites_checked"], 1)
            changed = copy.deepcopy(manifest)
            changed["sites"][0]["bytes"] = b"incorrect!".hex()
            with self.assertRaisesRegex(ValueError, "hook bytes differ"):
                VERIFY.verify(changed, executable)
            changed["sites"][0]["file_offset"] = 10000
            with self.assertRaisesRegex(ValueError, "file range"):
                VERIFY.verify(changed, executable)
            executable.write_bytes(b"other executable fixture")
            with self.assertRaisesRegex(ValueError, "identity"):
                VERIFY.verify(manifest, executable)

    def test_offline_evidence_cannot_claim_native_qualification(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest, executable = self.fixture(Path(directory))
            manifest.update(native_adapter_qualified=True, native_release_ready=True)
            report = VERIFY.verify(manifest, executable)
            self.assertFalse(report["native_adapter_qualified"])
            self.assertFalse(report["native_release_ready"])
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest))
            command = [sys.executable, str(ROOT / "scripts/verify_prepared_hooks.py"),
                       "--manifest", str(path), "--executable", str(executable)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(subprocess.run(command + ["--require-native"], capture_output=True).returncode, 2)
            manifest["sites"].append({"status": "requires-port", "uses": ["changed crafting route"]})
            path.write_text(json.dumps(manifest))
            self.assertEqual(subprocess.run(command + ["--require-complete"], capture_output=True).returncode, 2)

    def test_recorded_preparation_has_no_runtime_identity_or_release_claim(self):
        profile = json.loads((ROOT / "compatibility/bds-1.26.60-preparation.json").read_text())
        self.assertFalse(profile["native_release_ready"])
        self.assertIsNone(profile["endstone"]["build_version"])
        for relative in profile["prepared_hooks"].values():
            manifest = json.loads((ROOT / relative).read_text())
            self.assertFalse(manifest["native_adapter_qualified"])
            self.assertFalse(manifest["native_release_ready"])
            self.assertIsNone(manifest["endstone_runtime"])
            self.assertTrue(manifest["sites"])


if __name__ == "__main__":
    unittest.main()
