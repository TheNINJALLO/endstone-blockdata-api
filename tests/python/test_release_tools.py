from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = {"project": "blockdata","slug": "endstone-blockdata-api","plugin_prefix": "endstone_blockdata_bds_","bridge_prefix": "_endstone_blockdata_live","version": "0.4.5-beta.30"}


class TestReleaseTools(unittest.TestCase):
    def run_tool(self, script: str, *arguments: str, check: bool = True):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), *arguments],
            cwd=ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_package_round_trip_and_checksum_tamper_detection(self):
        scratch_root = ROOT / "build" / "release-tool-tests"
        scratch_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch_root) as temporary:
            workspace = Path(temporary)
            stage = workspace / "stage"
            release = workspace / "release"
            plugin = stage / "plugins" / (
                CONFIG["plugin_prefix"] + "1_26_33.dll"
            )
            plugin.parent.mkdir(parents=True)
            plugin.write_bytes(b"MZ" + bytes(range(64)))
            bridge = stage / "python" / "_endstone_blockdata_live.cp314-win_amd64.pyd"
            bridge.parent.mkdir(parents=True)
            bridge.write_bytes(b"MZ" + bytes(range(32)))
            package = stage / "python" / "example.py"
            package.write_text("VALUE = 1\n", encoding="utf-8")
            # A repeated packaging run must never hash a stale manifest into itself.
            (stage / "PACKAGE_MANIFEST.json").write_text("{}\n", encoding="utf-8")

            common = (
                "--version", CONFIG["version"],
                "--bds", "1.26.33",
                "--platform", "windows-x64",
            )
            self.run_tool(
                "package_release.py",
                "--project", CONFIG["project"],
                *common,
                "--stage", str(stage),
                "--release-dir", str(release),
            )
            self.run_tool(
                "verify_release_assets.py",
                "--slug", CONFIG["slug"],
                *common,
                "--release-dir", str(release),
            )

            raw = next(release.glob("*.dll"))
            raw.write_bytes(raw.read_bytes() + b"tampered")
            failed = self.run_tool(
                "verify_release_assets.py",
                "--slug", CONFIG["slug"],
                *common,
                "--release-dir", str(release),
                check=False,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("Checksum manifest mismatch", failed.stderr + failed.stdout)

    def test_rejects_invalid_native_bridge_in_archive(self):
        scratch_root = ROOT / "build" / "release-tool-tests"
        scratch_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch_root) as temporary:
            workspace = Path(temporary)
            stage = workspace / "stage"
            release = workspace / "release"
            plugin = stage / "plugins" / (CONFIG["plugin_prefix"] + "1_26_33.dll")
            plugin.parent.mkdir(parents=True)
            plugin.write_bytes(b"MZ" + bytes(range(64)))
            bridge = stage / "python" / "_endstone_blockdata_live.cp314-win_amd64.pyd"
            bridge.parent.mkdir(parents=True)
            bridge.write_bytes(b"not-a-pe-binary")
            common = (
                "--version", CONFIG["version"], "--bds", "1.26.33",
                "--platform", "windows-x64",
            )
            self.run_tool(
                "package_release.py", "--project", CONFIG["project"], *common,
                "--stage", str(stage), "--release-dir", str(release),
            )
            failed = self.run_tool(
                "verify_release_assets.py", "--slug", CONFIG["slug"], *common,
                "--release-dir", str(release), check=False,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("Unexpected binary format for archive member", failed.stderr + failed.stdout)

    def test_requires_exactly_one_native_bridge(self):
        cases = {
            "missing": [],
            "duplicate": [
                f"{CONFIG['bridge_prefix']}.cp314-win_amd64.pyd",
                f"{CONFIG['bridge_prefix']}.cp314-win_amd64-debug.pyd",
            ],
        }
        scratch_root = ROOT / "build" / "release-tool-tests"
        scratch_root.mkdir(parents=True, exist_ok=True)
        for label, bridge_names in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory(dir=scratch_root) as temporary:
                workspace = Path(temporary)
                stage = workspace / "stage"
                release = workspace / "release"
                plugin = stage / "plugins" / (CONFIG["plugin_prefix"] + "1_26_33.dll")
                plugin.parent.mkdir(parents=True)
                plugin.write_bytes(b"MZ" + bytes(range(64)))
                for bridge_name in bridge_names:
                    bridge = stage / "python" / bridge_name
                    bridge.parent.mkdir(parents=True, exist_ok=True)
                    bridge.write_bytes(b"MZ" + bytes(range(32)))
                common = (
                    "--version", CONFIG["version"], "--bds", "1.26.33",
                    "--platform", "windows-x64",
                )
                self.run_tool(
                    "package_release.py", "--project", CONFIG["project"], *common,
                    "--stage", str(stage), "--release-dir", str(release),
                )
                failed = self.run_tool(
                    "verify_release_assets.py", "--slug", CONFIG["slug"], *common,
                    "--release-dir", str(release), check=False,
                )
                self.assertNotEqual(failed.returncode, 0)
                self.assertIn("Expected exactly one", failed.stderr + failed.stdout)

    def test_rejects_wrong_python_bridge_abi(self):
        scratch_root = ROOT / "build" / "release-tool-tests"
        scratch_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch_root) as temporary:
            workspace = Path(temporary)
            stage = workspace / "stage"
            release = workspace / "release"
            plugin = stage / "plugins" / (CONFIG["plugin_prefix"] + "1_26_33.dll")
            plugin.parent.mkdir(parents=True)
            plugin.write_bytes(b"MZ" + bytes(range(64)))
            bridge = stage / "python" / f"{CONFIG['bridge_prefix']}.cp313-win_amd64.pyd"
            bridge.parent.mkdir(parents=True)
            bridge.write_bytes(b"MZ" + bytes(range(32)))
            common = (
                "--version", CONFIG["version"], "--bds", "1.26.33",
                "--platform", "windows-x64",
            )
            self.run_tool(
                "package_release.py", "--project", CONFIG["project"], *common,
                "--stage", str(stage), "--release-dir", str(release),
            )
            failed = self.run_tool(
                "verify_release_assets.py", "--slug", CONFIG["slug"], *common,
                "--release-dir", str(release), check=False,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("CPython 3.14", failed.stderr + failed.stdout)

    def test_rejects_unsafe_release_component(self):
        scratch_root = ROOT / "build" / "release-tool-tests"
        scratch_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch_root) as temporary:
            stage = Path(temporary) / "stage"
            stage.mkdir()
            result = self.run_tool(
                "package_release.py",
                "--project", CONFIG["project"],
                "--version", "../escape",
                "--bds", "1.26.33",
                "--platform", "windows-x64",
                "--stage", str(stage),
                "--release-dir", str(Path(temporary) / "release"),
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Invalid version value", result.stderr + result.stdout)

    def test_rejects_unsupported_blockdata_bds(self):
        scratch_root = ROOT / "build" / "release-tool-tests"
        scratch_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch_root) as temporary:
            stage = Path(temporary) / "stage"
            stage.mkdir()
            result = self.run_tool(
                "package_release.py",
                "--project", CONFIG["project"],
                "--version", CONFIG["version"],
                "--bds", "1.26.32",
                "--platform", "windows-x64",
                "--stage", str(stage),
                "--release-dir", str(Path(temporary) / "release"),
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unsupported BDS build", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
