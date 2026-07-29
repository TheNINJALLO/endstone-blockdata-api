## Unreleased

## 0.4.7

- Added exact live player inventory capture and writes for main inventory, armor, offhand, and Ender Chest slots.
- Added canonical bundle/storage-item NBT editing inside player inventory slots.
- Added full preflight item validation, whole-inventory revision conflicts, Python bridge methods, C++ service access, and portable tests.
- Added header-only C++ and Python views for vanilla bundles and custom `minecraft:storage_item` contents.
- Stabilized protected-branch check names and required release tags to identify a commit already merged into protected `main`.

## 0.4.6

- Added `/bd menu` and made bare `/bd` open a single guarded player form that navigates every registered locate, inspect, inventory, audit, and state command.
- Added strict form-result validation, stale-callback and duplicate-form suppression, permission rechecks, lifecycle cleanup, back navigation, and confirmations for inventory and block-state writes.
- Kept typed commands and console help fully available while adding route, malformed-input, close, send-failure, quit, death, and command-registration regression coverage to the CPython 3.14 test wheel.

## 0.4.5

- Promoted the beta.32 native API, package-local CPython 3.14 command wheels, and complete BDS 1.26.33 release bundles to the stable release line.
- Preserved the Endstone 0.11.6 compatibility target and `endstone:blockdata:v2` service ABI while publishing stable artifact names and release metadata.

## 0.4.5-beta.32

- Fixed every `/bd` coordinate overload to match Endstone 0.11's real argument contract, removed silent player-feet fallback, and added safe selected-container and explicit `at <x> <y> <z>` mutation targets.
- Made `/bd locate` filter actual containers, sort nearest-first, and report chest, barrel, and colored shulker capacity, occupied slots, item previews, and actor-capture misses.
- Added occupied-only native inventory snapshots, explicit container capacity and capture status, bounded exact actor/container access, and consistent reference-model container metadata.
- Versioned the cross-DSO service as `endstone:blockdata:v2` so mixed old/new native plugins and wheels fail lookup safely instead of sharing incompatible C++ layouts.
- Added registration tests for all 13 command usages plus regressions for negative coordinates, empty containers, sparse audit changes, invalid targets, conflicts, and bridge recovery.
- Included capture completeness and container metadata in snapshot revisions, and bounded `/bd inspect` canonical-NBT chat output with an explicit truncation count while keeping occupied inventory separately summarized.
- Preserved Linux host-resolved Endstone plugin imports while retaining selective build- and release-time rejection of unresolved private Bedrock ABI symbols.

## 0.4.5-beta.31

- Fixed Endstone 0.11 logger calls so the inspector passes one rendered string instead of unsupported logging-style positional arguments.
- Replaced the universal command wheel with exact-built CPython 3.14 Linux and Windows wheels that bundle `_endstone_blockdata_live` package-locally.
- Added strict package-local bridge loading that ignores stale top-level extensions and preserves dependency or ABI import failures.
- Added same-platform relocated-wheel smoke tests plus cross-platform wheel-tag, binary-format, entry-point, command, permission, and packaging validation.
- Included the matching wheel inside every complete BDS 1.26.33 ZIP and its per-platform checksum contract.

## 0.4.5-beta.30

- Normalized Endstone's `26.33` runtime build string against the packaged `1.26.33` target so the exact native adapter can enable on the supported server.
- Moved the command-test wheel and bundled live bridge validation to CPython 3.14, including required `cp314`/`cpython-314` ABI checks.
- Added safe Endstone v0.11.6 build-metadata/development-suffix validation and runtime-versus-expected mismatch diagnostics before public-adapter fallback.
- Pinned the wheel runtime, release interpreter, and proven Conan 2.31.1 toolchain so tagged rebuilds cannot silently drift from the supported Endstone 0.11.6 contract.

## 0.4.5-beta.29

- Replaced unsafe Linux Bedrock ABI stubs with the matching Endstone tag's real implementations, fixing the `ItemStackBase` destructor load failure and the other strong unresolved NBT/item symbols.
- Added a strong functional native item bridge that scopes the live Level registry and atomically resolves `CanPlaceOn`/`CanDestroy` without weak symbol shims.
- Focused exact native releases on BDS 1.26.33 with Endstone v0.11.6 for Linux and Windows.
- Added build- and package-time symbol gates plus relocatable-RPATH checks for both the native plugin and bundled Python bridge.
- Added deep-copy-safe NBT values, deterministic revisions, validated conflict policies, and stricter live patch/region input handling.
- Updated the Endstone 0.11 test wheel, registered `/bd` command metadata, exercised every handler, and made the live bridge requirement explicit.
- Synchronized release metadata and made CI publish complete ZIP/checksum assets and beta prereleases.

## 0.4.5-alpha.9

- Replaced one-off private-header downloads with Endstone's Conan dependency graph.
- Added the public Endstone Cloudsmith Conan remote for the patched `raknet/4.081-mojang` recipe.
- Added Boost, EnTT, GLM, magic_enum, Microsoft GSL, base64, fmt, expected-lite and RakNet package wiring.
- Added Conan profile/toolchain generation for Clang 18/libc++ on Linux and clang-cl/lld-link on Windows.
- Kept exact BDS 1.26.32 and 1.26.33 builds isolated and diagnostic.

## 0.4.5-alpha.9

- Fixed the Endstone plugin macro inheritance error by removing `final` from plugin classes.
- Switched exact Windows builds to clang-cl, lld-link and Ninja inside the Visual Studio 2022 developer environment.
- Added the exact RakNet header source required by Endstone private Bedrock headers.
- Synchronized workflow, package, CMake and source-release versions.
- Included the actual hidden `.github/workflows/ci.yml` files in the release package.

# Changelog

## 0.4.5-alpha.9

### Fixed

- Fixed Linux exact-build exit code 126 by invoking `scripts/build_exact.sh` through `bash`; the build no longer depends on Git preserving an executable bit.
- Moved Linux exact builds to Ubuntu 24.04 with explicit Clang 18, libc++ 18 and libc++abi 18.
- Replaced the unsupported Windows `clang-cl`/Ninja exact build with Visual Studio 2022 and MSVC x64.
- Added native-command exit checks to the PowerShell build script.
- Added failed-build diagnostic artifacts containing CMake logs and cache data.
- Hardened exact-build version/platform validation and release checksum generation.

## 0.4.5-alpha.9

- Added deterministic CMake install layouts for exact native builds.
- Added stable BDS- and platform-specific plugin filenames.
- Added raw `.dll`/`.so`, complete ZIP package, package manifest, and SHA-256 generation.
- Added GitHub Actions artifact uploads for every exact Windows and Linux build.
- Added automatic GitHub Release publishing when tag `v0.4.5-alpha.9` is pushed.
- Added release-tag validation and repeatable release asset replacement.
- Removed the unpinned Windows Ninja action and install Ninja through Python instead.
- Added package-integrity verification before artifacts are uploaded.

## 0.4.5-alpha.9

- Added complete canonical live block-actor NBT capture for supported containers.
- Added every container slot and nested item user-data tag, including enchantments, lore, custom data, `CanPlaceOn`, and `CanDestroy`.
- Added supported actor/container NBT writes, resulting-tag validation, dirty marking, and client updates.
- Registered the live API as Endstone service `endstone:blockdata`.
- Added `_endstone_blockdata_live` Python bridge source for live captures from Python plugins.
- Added C++ and Python anti-grief container capture examples.
- Added inventory-level audit diffs and fixed initial in-memory snapshot location handling.
- Made whole-container `Items` replacement transactional: the adapter validates every slot and item before mutating the live container.

## 0.2.0-alpha.2

- Added exact Minecraft Bedrock 26.30-family runtime gate.
- Pinned BDS 1.26.32 to Endstone v0.11.5 and BDS 1.26.33 to Endstone v0.11.6.
- Added native block-actor lookup through the exact Endstone dimension implementation.
- Added block-actor metadata, typed container inventory, container save-SNBT capture, dirty marking, and client update calls.
- Added exact-build shell and PowerShell build scripts.
- Added Windows/Linux GitHub Actions source-build matrix for both supported BDS builds.
- Kept arbitrary raw BlockActor NBT round-trip disabled because the required general save/load ABI is not publicly declared by these Endstone versions.

## 0.1.0-alpha.1

- Initial portable BlockData architecture and public Endstone block state adapter.
