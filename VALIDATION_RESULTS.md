# Validation results

Validated locally on 2026-08-07:

- Python unit, release-tool, metadata, native source-guard, strict logger, command-overload, form-navigation, shelf-shop, and bridge-loader tests (76/76)
- Official BDS `1.26.40.8` Linux and Windows archive downloads and SHA-256 checksums
- Linux and Windows storage-item, tracker, and container-lifetime RVA mapping with instruction-fingerprint verification
- Platform-wheel contracts for entry points, native-plugin dependencies, commands,
  permissions, CPython 3.14 tags, package-local bridges, binary magic, and RECORD integrity
- Project/version/dependency metadata consistency for `0.5.2`
- GitHub Actions YAML parsing
- Release packaging round-trip with a synthetic Windows plugin stage
- Checksum, ZIP path, manifest, native bridge, unresolved Bedrock/private Endstone-core symbol,
  CPython 3.14 SOABI, dynamic runtime dependency, and non-relocatable RPATH
  rejection gates
- Stable release filenames for BDS 1.26.40 on Linux and Windows
- `git diff --check`

Not validated locally in this environment:

- Portable C++ compilation and CTest because CMake is not installed locally
- Exact Linux and Windows Endstone/Bedrock native builds and relocated CPython 3.14 wheel imports; these are delegated to the GitHub Actions matrix
- Loading the exact native `.dll` or `.so` inside BDS 1.26.40 / Endstone 0.11.8
- Live container mutation against a production world
