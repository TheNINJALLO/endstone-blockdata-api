# Endstone 0.11.13 / BDS 1.26.52.3 validation

6 CTest checks and 85 Python tests passed. The packaged native plugin and matching CPython 3.14 wheel passed live behavioral checks, save/query/resume, and clean shutdown in disposable servers.

Evidence: `compatibility/native-qualification.json`. Network protocol remains 2193. Previous results below refer to earlier releases.

# Endstone 0.11.12 validation

Current evidence is in `compatibility/native-qualification.json`; the server remains BDS 1.26.51.1. The records below describe the previous 0.11.11 release.

# Validation results

## BDS 1.26.51 / Endstone 0.11.11 target

The active compatibility target is **game 1.26.51**, server package
**1.26.51.1**, and **Endstone 0.11.11**. Source command wheels require
**Endstone >=0.11.11**, with no upper bound. Both official server archives
have been checksum-verified and the matching SDK commit is recorded.
The native adapter port and live validation remain pending.
See [target details and verification commands](docs/BDS_1_26_51.md).
The release information below describes the previous exact server target.



## 0.6.3

Validated locally on 2026-09-09:

- CPython 3.14 Python tests (76/76) and synchronized release metadata
- Compiled the versioned Windows live bridge and built/imported its relocated
  v0.6.3 wheel
- Native-wheel regression checks store canonical JSON and diagnostic SNBT in
  SQLite TEXT, read them back, and restore the exact NBT bytes; coverage includes
  the reported `0x8a` byte at position 6125, malformed UTF-8, all byte values,
  valid Unicode, embedded NULs, nested NBT, and compound keys
- `git diff --check`

The required CI matrix builds and verifies both complete platform packages
before merge and release. Live BDS server validation has not been performed.
Consumers still need `ensure_ascii=True` when persisting canonical NBT as JSON.

## 0.6.2

Validated locally on 2026-09-08:

- CPython 3.14 Python tests (76/76) and synchronized release metadata
- The UTF-8 fix compiled into the Windows live bridge, with relocated-wheel
  tests covering truncated and invalid UTF-8, all 256 byte values, Unicode,
  embedded NULs, compound keys, JSON persistence, and String/ByteArray types
  (tested before the release version bump)
- `git diff --check`

The release workflow builds and validates the versioned Windows and Linux
packages before publishing. Live BDS 1.26.45 / Endstone 0.11.10 server testing
remains required.

## 0.6.1

Validated locally on 2026-08-28:

- Python unit, release-tool, metadata, native source-guard, strict logger,
  command-overload, form-navigation, shelf-shop, and bridge-loader tests under
  CPython 3.14 (76/76)
- Portable C++ compilation with MSVC 19.44 and all CTest targets (6/6)
- Official BDS `1.26.45.1` Linux and Windows archive downloads and SHA-256 checksums
- Linux and Windows storage-item, tracker, and container-lifetime RVA mapping with instruction-fingerprint verification
- Exact Windows x64 native plugin and live Python bridge compilation against
  Endstone v0.11.10 with CPython 3.14, clang-cl 22.1.8, lld-link, Ninja, and the
  pinned Conan dependency graph
- Windows release DLL, ZIP, wheel, and checksum generation plus independent
  release-asset validation
- Relocated Windows wheel install/import, entry point, command, permission,
  CPython 3.14 tag, package-local bridge, binary-magic, and RECORD-integrity checks
- Project/version/dependency metadata consistency for `0.6.1`
- GitHub Actions YAML parsing
- Release packaging round-trip with a synthetic Windows plugin stage
- Checksum, ZIP path, manifest, native bridge, unresolved Bedrock/private Endstone-core symbol,
  CPython 3.14 SOABI, dynamic runtime dependency, and non-relocatable RPATH
  rejection gates
- Stable release filenames for BDS 1.26.45 on Linux and Windows
- `git diff --check`

Not validated locally in this environment:

- Exact Linux native compilation and relocated Linux CPython 3.14 wheel import;
  these remain delegated to the GitHub Actions matrix
- Loading the exact native `.dll` or `.so` inside a running BDS 1.26.45 /
  Endstone 0.11.10 server
- Live container mutation against a production world
