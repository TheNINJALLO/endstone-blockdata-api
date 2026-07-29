from __future__ import annotations

import re
import unittest
from pathlib import Path

from scripts.verify_release_assets import is_forbidden_undefined_symbol


ROOT = Path(__file__).resolve().parents[2]


class TestNativeSourceGuards(unittest.TestCase):
    def test_linux_plugin_preserves_host_imports_and_gates_private_bedrock_symbols(self):
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        link_options = re.findall(
            r"target_link_options\(\s*blockdata_api\b[^)]*\)",
            cmake,
            flags=re.DOTALL,
        )
        self.assertTrue(link_options)
        for option in link_options:
            self.assertNotIn("--no-undefined", option)
            self.assertNotIn("-z,defs", option)

        post_build = re.search(
            r"add_custom_command\(TARGET blockdata_api POST_BUILD(?P<body>.*?)\n\s*\)",
            cmake,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(post_build)
        body = post_build.group("body")
        self.assertIn("$<TARGET_FILE:blockdata_api>", body)
        self.assertIn("verify_no_undefined_bedrock_symbols.cmake", body)

        clean_symbols = (ROOT / "tests/cmake/nm_clean.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn("_ZN8endstone6Server8getLevelEv U", clean_symbols)

        symbol_gate = (
            ROOT / "cmake/verify_no_undefined_bedrock_symbols.cmake"
        ).read_text(encoding="utf-8")
        self.assertIn("N?8endstone4core", symbol_gate)
        player_rtti = (
            ROOT / "tests/cmake/nm_undefined_endstone_player.txt"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            player_rtti.strip(), "_ZTIN8endstone4core14EndstonePlayerE U"
        )
        self.assertTrue(
            is_forbidden_undefined_symbol(
                "_ZTIN8endstone4core14EndstonePlayerE"
            )
        )
        self.assertTrue(
            is_forbidden_undefined_symbol(
                "_ZNK8endstone4core17EndstoneDimension9getHandleEv"
            )
        )
        for symbol in (
            "_ZN23DynamicContainerTrackerD2Ev",
            "_ZN23DynamicContainerManager12giveLifetimeER14ContainerOwner",
            "_ZN24IContainerRegistryAccessD2Ev",
            "_ZN25IContainerRegistryTrackerD2Ev",
        ):
            with self.subTest(symbol=symbol):
                self.assertTrue(is_forbidden_undefined_symbol(symbol))
        self.assertFalse(
            is_forbidden_undefined_symbol("_ZN8endstone6Server8getLevelEv")
        )

    def test_player_inventory_adapter_does_not_import_private_player_rtti(self):
        adapter = (
            ROOT / "src/bds_26_30_player_inventory_adapter.cpp"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            "dynamic_cast<endstone::core::EndstonePlayer", adapter
        )
        self.assertNotIn("typeid(endstone::core::EndstonePlayer", adapter)
        self.assertNotIn('"endstone/core/player.h"', adapter)
        self.assertNotIn('"bedrock/world/actor/player/player.h"', adapter)
        self.assertNotIn("EndstonePlayer", adapter)
        self.assertNotIn("sendInventory", adapter)
        self.assertEqual(adapter.count("if (!player.isValid())"), 2)
        self.assertIn("containsStorageItemWrite", adapter)
        self.assertIn("live player bundle/storage-item writes are disabled", adapter)

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
        self.assertIn('PATTERN "__pycache__" EXCLUDE', cmake)
        self.assertIn('PATTERN "*.pyc" EXCLUDE', cmake)

    def test_native_item_bridge_is_functional_and_scoped(self):
        cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
        bridge = (ROOT / "src/native_item_bridge.cpp").read_text(encoding="utf-8")
        adapter = (ROOT / "src/bds_26_30_adapter.cpp").read_text(encoding="utf-8")

        self.assertIn("src/native_item_bridge.cpp", cmake)
        self.assertIn("thread_local Level *active_item_registry_level", bridge)
        self.assertIn("active_item_registry_level->getItemRegistry()", bridge)
        self.assertEqual(bridge.count("_loadBlocksForCanPlaceOnCanDestroy"), 2)
        self.assertEqual(bridge.count("_updateCompareHashes()"), 2)
        self.assertIn("ConstructibleWeakRef", bridge)
        self.assertIn("CreateTrackerRva", bridge)
        self.assertIn("TrackStorageItemRva", bridge)
        self.assertIn("ReceiveContainerLifetimesRva", bridge)
        self.assertIn("ManagerGiveLifetimeRva", bridge)
        self.assertIn("NativeStorageItemTransaction::materialize", bridge)
        self.assertNotIn("tryMoveStorageItem", bridge)
        self.assertNotIn("force-unresolved", cmake.lower())
        self.assertIn("NativeItemRegistryScope item_registry_scope(*access->level)", adapter)
        self.assertIn("requested_storage->replaceContainerLifetimes", adapter)
        self.assertIn("rollback_storage->replaceContainerLifetimes", adapter)
        self.assertIn("requested_storage->escrowContainerLifetimes", adapter)
        self.assertNotIn("insert_or_assign", adapter)
        self.assertIn("validContainerOwnerStorage", bridge)
        self.assertIn("MaxOwnedContainerLifetimes", bridge)
        self.assertIn("auto *owner = containerOwner(container)", bridge)

        capture = adapter[
            adapter.index("std::optional<BlockSnapshot> capture"):
            adapter.index("ApplyResult apply")
        ]
        self.assertLess(
            capture.index("if (!access)"),
            capture.index("NativeItemRegistryScope item_registry_scope"),
        )
        self.assertLess(
            capture.index("NativeItemRegistryScope item_registry_scope"),
            capture.index("captureCanonicalActorTag"),
        )
        self.assertLess(
            bridge.index("item.setNull(std::nullopt)"),
            bridge.index("item = *tracked"),
        )
        apply = adapter[adapter.index("ApplyResult apply"):]
        self.assertLess(
            apply.index("requested_storage->escrowContainerLifetimes"),
            apply.index("access->container->setItem("),
        )
        self.assertLess(
            adapter.index("NativeItemRegistryScope item_registry_scope"),
            adapter.index("NativeMutationPlan plan"),
        )

    def test_block_actor_capture_is_typed_and_inventory_is_sparse(self):
        adapter = (ROOT / "src/bds_26_30_adapter.cpp").read_text(encoding="utf-8")
        bridge = (ROOT / "src/live_python_bindings.cpp").read_text(encoding="utf-8")

        self.assertIn(
            "auto *vanilla = static_cast<VanillaBlockActor *>(actor)",
            adapter,
        )
        self.assertIn(
            "static_cast<IVanillaMainBlockActorComponent *>(vanilla)",
            adapter,
        )
        self.assertNotIn("reinterpret_cast<VanillaBlockActor *>(actor)", adapter)
        self.assertNotIn(
            "reinterpret_cast<std::byte *>(actor) + sizeof(BlockActor)",
            adapter,
        )
        self.assertIn("if (stack.isNull()) continue;", adapter)
        self.assertIn(
            "if (!access) {\n            snapshot->revision = calculateRevision(*snapshot);",
            adapter,
        )
        self.assertIn('out["block_entity_status"]', bridge)
        self.assertIn('actor["is_container"]', bridge)
        self.assertIn('actor["container_size"]', bridge)
        self.assertIn("auto updated = capture(patch.location);", adapter)
        self.assertIn(
            "result.resulting_revision = updated ? updated->revision : 0;",
            adapter,
        )

    def test_live_service_name_is_abi_versioned(self):
        service = (ROOT / "include/endstone_blockdata/live_service.h").read_text(
            encoding="utf-8"
        )
        self.assertIn('BlockDataServiceName = "endstone:blockdata:v2"', service)
        self.assertIn("BlockDataServiceAbiVersion = 2", service)


if __name__ == "__main__":
    unittest.main()
