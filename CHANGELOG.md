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
