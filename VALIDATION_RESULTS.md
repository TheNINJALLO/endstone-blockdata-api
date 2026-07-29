# Validation results

Validated on 2026-07-29:

- Portable MSVC Release configuration and C++20 build
- CTest BlockData suite (6/6)
- Python unit, release-tool, metadata, native source-guard, strict logger, command-overload, form-navigation, shelf-shop, and bridge-loader tests (76/76)
- Platform-wheel contracts for entry points, native-plugin dependencies, commands,
  permissions, CPython 3.14 tags, package-local bridges, binary magic, and RECORD integrity
- Project/version/dependency metadata consistency for `0.4.9`
- GitHub Actions YAML parsing
- Release packaging round-trip with a synthetic Windows plugin stage
- Checksum, ZIP path, manifest, native bridge, unresolved Bedrock/private Endstone-core symbol,
  CPython 3.14 SOABI, dynamic runtime dependency, and non-relocatable RPATH
  rejection gates
- Stable release filenames for BDS 1.26.33 on Linux and Windows
- Exact Windows clang-cl/lld-link build of the BDS 1.26.33 plugin and CPython 3.14 bridge
- Relocated Windows CPython 3.14 v0.4.9 wheel import, bridge-version handshake,
  nested bundle NBT round-trip, typed-scalar bounds, and `/bd` registration
- Exact install-stage exclusion of local Python bytecode caches
- Source ZIP integrity and `git diff --check`

Not validated in this environment:

- Exact Linux Endstone/Bedrock native build and relocated CPython 3.14 wheel import
  from the GitHub Actions matrix
- Loading the exact native `.dll` or `.so` inside BDS 1.26.33 / Endstone 0.11.6
- Live container mutation against a production world
