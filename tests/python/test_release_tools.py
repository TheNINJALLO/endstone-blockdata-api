from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[2]
CONFIG = {"project": "blockdata","slug": "endstone-blockdata-api","plugin_prefix": "endstone_blockdata_bds_","bridge_prefix": "_endstone_blockdata_live","wheel_prefix": "endstone_blockdata_inspector","version": "0.4.6"}


class TestReleaseTools(unittest.TestCase):
    def run_tool(self, script: str, *arguments: str, check: bool = True):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), *arguments],
            cwd=ROOT,
            check=check,
            capture_output=True,
            text=True,
        )

    def test_combined_release_asset_set_is_exact_and_nonempty(self):
        scratch_root = ROOT / "build" / "release-tool-tests"
        scratch_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch_root) as temporary:
            release = Path(temporary)
            stem = f"{CONFIG['slug']}-v{CONFIG['version']}-bds-1.26.33"
            names = {
                f"{stem}-linux-x64.so",
                f"{stem}-linux-x64.zip",
                f"{stem}-linux-x64.sha256",
                f"{stem}-windows-x64.dll",
                f"{stem}-windows-x64.zip",
                f"{stem}-windows-x64.sha256",
                f"{CONFIG['wheel_prefix']}-{CONFIG['version']}-cp314-cp314-linux_x86_64.whl",
                f"{CONFIG['wheel_prefix']}-{CONFIG['version']}-cp314-cp314-win_amd64.whl",
            }
            for name in names:
                (release / name).write_bytes(b"asset")
            common = (
                "--slug", CONFIG["slug"], "--version", CONFIG["version"],
                "--bds", "1.26.33", "--release-dir", str(release),
            )
            self.run_tool("verify_combined_release_assets.py", *common)
            (release / "unexpected.txt").write_bytes(b"unexpected")
            failed = self.run_tool(
                "verify_combined_release_assets.py", *common, check=False
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("Release asset set mismatch", failed.stderr + failed.stdout)

    @staticmethod
    def add_command_wheel(stage: Path) -> Path:
        wheel = (
            stage / "plugins" /
            "endstone_blockdata_inspector-0.4.6-cp314-cp314-win_amd64.whl"
        )
        wheel.parent.mkdir(parents=True, exist_ok=True)
        bridges = sorted((stage / "python").glob("_endstone_blockdata_live.*"))
        with ZipFile(wheel, "w", compression=ZIP_DEFLATED) as archive:
            if bridges:
                archive.writestr(
                    f"endstone_blockdata_inspector/{bridges[0].name}",
                    bridges[0].read_bytes(),
                )
        return wheel

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
            self.add_command_wheel(stage)
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
            self.add_command_wheel(stage)
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
                self.add_command_wheel(stage)
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
            self.add_command_wheel(stage)
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
