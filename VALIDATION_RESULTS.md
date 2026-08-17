# Validation results

Validated locally on 2026-08-17:

- Python unit, release-tool, metadata, native source-guard, strict logger,
  command-overload, form-navigation, shelf-shop, and bridge-loader tests under
  CPython 3.14 (76/76)
- Portable C++ compilation with MSVC 19.44 and all CTest targets (6/6)
- Official BDS `1.26.44.3` Linux and Windows archive downloads and SHA-256 checksums
- Linux and Windows storage-item, tracker, and container-lifetime RVA mapping with instruction-fingerprint verification
- Exact Windows x64 native plugin and live Python bridge compilation against
  Endstone v0.11.9 with CPython 3.14, clang-cl 22.1.8, lld-link, Ninja, and the
  pinned Conan dependency graph
- Windows release DLL, ZIP, wheel, and checksum generation plus independent
  release-asset validation
- Relocated Windows wheel install/import, entry point, command, permission,
  CPython 3.14 tag, package-local bridge, binary-magic, and RECORD-integrity checks
- Project/version/dependency metadata consistency for `0.6.0`
- GitHub Actions YAML parsing
- Release packaging round-trip with a synthetic Windows plugin stage
- Checksum, ZIP path, manifest, native bridge, unresolved Bedrock/private Endstone-core symbol,
  CPython 3.14 SOABI, dynamic runtime dependency, and non-relocatable RPATH
  rejection gates
- Stable release filenames for BDS 1.26.44 on Linux and Windows
- `git diff --check`

Not validated locally in this environment:

- Exact Linux native compilation and relocated Linux CPython 3.14 wheel import;
  these remain delegated to the GitHub Actions matrix
- Loading the exact native `.dll` or `.so` inside a running BDS 1.26.44 /
  Endstone 0.11.9 server
- Live container mutation against a production world
