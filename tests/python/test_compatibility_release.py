from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "compatibility_release", ROOT / "scripts/package_compatibility_release.py")
RELEASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RELEASE)


class CompatibilityReleaseTests(unittest.TestCase):
    def setUp(self):
        self.source = json.loads((ROOT / "SOURCE_RELEASE.json").read_text(encoding="utf-8"))

    def test_release_cannot_claim_native_or_stable_qualification(self):
        RELEASE.validate_release(self.source)
        for field, value in (("native_release_ready", True), ("version", "1.2.3"),
                             ("release_channel", "stable"), ("python_version", "0.0.0")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                RELEASE.validate_release({**self.source, field: value})

    def test_wheel_rejects_native_binaries_and_command_plugins(self):
        with tempfile.TemporaryDirectory() as directory:
            wheel = Path(directory) / "api.whl"
            for extra, contents in ((None, ""), ("api/bridge.pyd", "native"),
                                    ("api.dist-info/entry_points.txt", "[endstone]\nplugin=api:Plugin\n")):
                with self.subTest(extra=extra):
                    with ZipFile(wheel, "w") as archive:
                        archive.writestr("api.dist-info/METADATA",
                                         f"Name: {self.source['name']}\nVersion: {self.source['python_version']}\n")
                        archive.writestr("api.dist-info/WHEEL",
                                         "Root-Is-Purelib: true\nTag: py3-none-any\n")
                        if extra:
                            archive.writestr(extra, contents)
                    if extra:
                        with self.assertRaises(ValueError):
                            RELEASE.verify_wheel(wheel, self.source)
                    else:
                        RELEASE.verify_wheel(wheel, self.source)


if __name__ == "__main__":
    unittest.main()
