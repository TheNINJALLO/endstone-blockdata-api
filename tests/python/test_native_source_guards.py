from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class TestNativeSourceGuards(unittest.TestCase):
    def test_native_runtime_gate_uses_normalized_expected_builds(self):
        adapter = (ROOT / "src/bds_26_30_adapter.cpp").read_text(encoding="utf-8")
        plugin = (ROOT / "src/plugin.cpp").read_text(encoding="utf-8")
        version_gate = (ROOT / "src/version_gate.cpp").read_text(encoding="utf-8")

        self.assertIn("isExpectedBds2630Build(server.getMinecraftVersion()", adapter)
        self.assertNotIn(
            "server.getMinecraftVersion() == ENDSTONE_BLOCKDATA_BDS_BUILD",
            adapter,
        )
        self.assertIn('canonicalBdsBuild(build) == "26.33"', version_gate)
        self.assertIn("runtime BDS={} Endstone={}; expected BDS={} Endstone={}", plugin)

    def test_exact_result_patch_and_install_components_are_guarded(self):
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        self.assertIn('set(ENDSTONE_EXACT_TAG "v0.11.6")', cmake)
        self.assertIn('std::string(\\"Error: \\") + error', cmake)
        self.assertIn('set(ENDSTONE_RESULT_ERROR_FORMAT "std::format(\\"{}\\", error_info.error)")', cmake)
        self.assertIn('set(ENDSTONE_RESULT_ERROR_MESSAGE "error_info.error.message()")', cmake)
        self.assertIn("result.h no longer contains the expected std::error_code", cmake)
        for artifact, destination in (
            ("RUNTIME", "plugins"),
            ("LIBRARY", "plugins"),
            ("ARCHIVE", "lib"),
            ("RUNTIME", "python"),
            ("LIBRARY", "python"),
        ):
            self.assertIn(
                f"{artifact} DESTINATION {destination} COMPONENT blockdata_package",
                cmake,
            )

    def test_native_item_bridge_is_functional_and_scoped(self):
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        bridge = (ROOT / "src/native_item_bridge.cpp").read_text(encoding="utf-8")
        adapter = (ROOT / "src/bds_26_30_adapter.cpp").read_text(encoding="utf-8")

        self.assertIn("src/native_item_bridge.cpp", cmake)
        self.assertIn("thread_local Level *active_item_registry_level", bridge)
        self.assertIn("active_item_registry_level->getItemRegistry()", bridge)
        self.assertEqual(bridge.count("_loadBlocksForCanPlaceOnCanDestroy"), 2)
        self.assertEqual(bridge.count("_updateCompareHashes()"), 2)
        self.assertNotIn("weak", bridge.lower())
        self.assertNotIn("force-unresolved", cmake.lower())
        self.assertIn("NativeItemRegistryScope item_registry_scope(*access->level)", adapter)
        self.assertLess(
            adapter.index("NativeItemRegistryScope item_registry_scope"),
            adapter.index("NativeMutationPlan plan"),
        )


if __name__ == "__main__":
    unittest.main()
