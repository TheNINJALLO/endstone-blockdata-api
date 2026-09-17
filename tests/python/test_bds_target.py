from __future__ import annotations

import copy
import importlib.util
import json
import struct
import subprocess
import sys
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "prepare_bds_target", ROOT / "scripts/prepare_bds_target.py"
)
assert SPEC is not None and SPEC.loader is not None
TARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGET)


def linux_executable() -> bytes:
    header = bytearray(64)
    header[:7] = b"\x7fELF\x02\x01\x01"
    struct.pack_into("<H", header, 18, 62)
    struct.pack_into("<Q", header, 32, 64)
    struct.pack_into("<HH", header, 54, 56, 1)
    note = struct.pack("<III", 4, 20, 3) + b"GNU\0" + b"\xab" * 20
    segment = struct.pack("<IIQQQQQQ", 4, 0, 120, 0, 0, len(note), len(note), 4)
    return bytes(header) + segment + note


def windows_executable() -> bytes:
    header = bytearray(64)
    header[:2] = b"MZ"
    struct.pack_into("<I", header, 60, 64)
    return bytes(header) + b"PE\0\0\x64\x86" + b"\0" * 18 + b"\x0b\x02"


class TestBdsTarget(unittest.TestCase):
    def test_endstone_minimum_has_no_upper_bound(self):
        for version in ("0.11.11", "v0.11.11", "0.11.12", "0.11.100", "0.12.0", "1.0.0",
                        "0.11.11.dev1", "0.11.11-dev.2+build.7", "v0.11.11+local"):
            with self.subTest(version=version):
                self.assertTrue(TARGET.endstone_at_least(version, "0.11.11"))
        for version in ("", "0.11.10", "0.11.9", "0.10.100", "0.11", "0.11.11.1", "0.11.11evil",
                        "0.11.11+", "0.11.11-dev..1", "0.11.11\n", "00.11.11", "latest"):
            with self.subTest(version=version):
                self.assertFalse(TARGET.endstone_at_least(version, "0.11.11"))

    def test_recorded_target_selects_known_endstone_and_keeps_native_qualification_explicit(self):
        profile = json.loads((ROOT / "compatibility/bds-1.26.51.json").read_text())
        self.assertEqual(profile["bds_package"], "1.26.51.1")
        self.assertEqual(profile["endstone"]["requirement"], ">=0.11.11")
        self.assertIsNone(profile["endstone"]["maximum_version"])
        self.assertEqual(profile["endstone"]["build_version"], "0.11.11")
        self.assertEqual(profile["endstone"]["source_commit"], "37b395378d91d6d20f1c52bf9d79dbd20e152458")
        self.assertEqual(TARGET.DEFAULT_TARGET.name, "bds-1.26.51.json")
        self.assertEqual(profile["game_version"], "1.26.51")
        self.assertEqual(profile["status"], "pending-native-adapter-qualification")
        metadata = json.loads((ROOT / "compatibility/versions.json").read_text())
        self.assertEqual(metadata["endstone_requirement"], ">=0.11.11")
        self.assertEqual(metadata["pending_targets"][0]["bds_package"], "1.26.51.1")
        wheel_projects = {
            "endstone-blockdata-api": "examples/python/block_data_inspector_plugin/pyproject.toml",
            "endstone-worldgen-api": "examples/python/world_gen_studio_plugin/pyproject.toml",
            "endstone-enchantment-api": "partner/pyproject.toml",
        }
        wheel = tomllib.loads((ROOT / wheel_projects[profile["project"]]).read_text())
        requirement = [item for item in wheel["project"]["dependencies"] if item.startswith("endstone")]
        self.assertEqual(requirement, ["endstone>=0.11.11"])
        for platform in ("linux-x64", "windows-x64"):
            for kind in ("archive", "executable"):
                entry = profile["server_files"][platform][kind]
                self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")
                self.assertGreater(entry["size_bytes"], 0)

    def test_archive_identity_tampering_and_native_release_gate(self):
        scratch = ROOT / "build" / "target-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            folder = Path(directory)
            for platform, filename, executable in (
                ("linux-x64", "bedrock_server", linux_executable()),
                ("windows-x64", "bedrock_server.exe", windows_executable()),
            ):
                with self.subTest(platform=platform):
                    archive = folder / f"{platform}.zip"
                    with zipfile.ZipFile(archive, "w") as zipped:
                        zipped.writestr(filename, executable)
                    identity = TARGET.inspect_archive(archive, platform)
                    if platform == "linux-x64":
                        self.assertEqual(identity["executable"]["gnu_build_id"], "ab" * 20)
                    profile = {
                        "bds_package": "1.26.51.1", "bds_runtime": "26.51",
                        "endstone": {"requirement": ">=0.11.11", "minimum_version": "0.11.11", "build_version": "0.11.11"},
                        "status": "pending-native-adapter-qualification",
                        "qualification_required": ["matching Endstone runtime"],
                        "server_files": {platform: identity},
                    }
                    # A renamed ZIP is acceptable; its bytes must still match.
                    profile["server_files"][platform]["archive"]["filename"] = "original.zip"
                    report = TARGET.prepare(profile, archive, platform, "0.12.0")
                    self.assertTrue(report["server_files_verified"])
                    self.assertFalse(report["native_adapter_qualified"])
                    self.assertEqual(TARGET.prepare(profile, archive, platform, None)["selected_endstone_version"], "0.11.11")
                    self.assertEqual(report["profile_endstone_version"], "0.11.11")
                    self.assertEqual(report["selected_endstone_version"], "0.12.0")
                    with self.assertRaisesRegex(ValueError, "Endstone must be"):
                        TARGET.prepare(profile, archive, platform, "0.11.10")
                    for kind in ("archive", "executable"):
                        corrupt = copy.deepcopy(profile)
                        corrupt["server_files"][platform][kind]["sha256"] = "0" * 64
                        with self.assertRaisesRegex(ValueError, f"{kind} sha256 mismatch"):
                            TARGET.prepare(corrupt, archive, platform, None)
                    profile_path = folder / "profile.json"
                    profile_path.write_text(json.dumps(profile))
                    command = [sys.executable, str(ROOT / "scripts/prepare_bds_target.py"),
                               "--archive", str(archive), "--platform", platform,
                               "--target", str(profile_path)]
                    prepared = subprocess.run(command, capture_output=True, text=True)
                    self.assertEqual(prepared.returncode, 0, prepared.stderr)
                    blocked = subprocess.run(command + ["--require-native"], capture_output=True, text=True)
                    self.assertEqual(blocked.returncode, 2, blocked.stderr)
                    self.assertFalse(json.loads(blocked.stdout)["native_adapter_qualified"])
                    with zipfile.ZipFile(archive, "w") as zipped:
                        zipped.writestr(filename, b"not an executable")
                    with self.assertRaises(ValueError):
                        TARGET.inspect_archive(archive, platform)


if __name__ == "__main__":
    unittest.main()
