# Build status

## BDS 1.26.51 / Endstone 0.11.11 target

The active compatibility target is **game 1.26.51**, server package
**1.26.51.1**, and **Endstone 0.11.11**. Source command wheels require
**Endstone >=0.11.11**, with no upper bound. Both official server archives
have been checksum-verified and the matching SDK commit is recorded.
The native adapter port and live validation remain pending.
See [target details and verification commands](docs/BDS_1_26_51.md).
The release information below describes the previous exact server target.



Version: **0.6.4-alpha.1**

## Implemented

- Portable C++ BlockData core and tests
- Python package and tests
- Exact BDS 1.26.45 / Endstone v0.11.10 adapter source
- Canonical container block-actor NBT and nested item data
- Native service and live Python bridge
- Deterministic native install and packaging scripts
- GitHub Actions Windows x64 and Linux x64 exact builds for BDS 1.26.45
- Downloadable workflow artifacts on every push
- Automatic tagged GitHub Releases
- Raw plugin, ZIP package, manifest, and SHA-256 outputs
- Verified CPython 3.14 platform command wheels with a bundled native bridge
- Build- and release-time rejection of unresolved Bedrock ABI and private Endstone-core symbols, plus release-time RPATH validation
- Strong native item-registry and placement/destroy restriction bridge with scoped live Level access
- ABI-versioned `endstone:blockdata:v2` service and matching package-local bridge
- Sparse occupied-slot snapshots with explicit container capacity and capture status
- Non-destructive live bundle-content flattening and transactional bundle writes
- Shelf and Chiseled Bookshelf live views, edits, diagnostics, and shop example

## Validation boundary

Package tooling, Python tests, the portable C++ targets, and the exact Windows
native release have been built and validated locally. The exact Linux release
is compiled by the included GitHub Actions runner. Both platforms still require
first-load testing inside BDS 1.26.45 / Endstone 0.11.10 before production use.

## GitHub Actions toolchain hotfix

- Linux exact builds run on Ubuntu 22.04 with Clang 18 and libc++ 18.
- Both platforms invoke `scripts/build_exact.py`, so executable-bit loss cannot cause exit code 126.
- Windows exact builds use clang-cl, lld-link, and Ninja inside the Visual Studio 2022 developer environment.
- Failed exact jobs upload CMake diagnostics for inspection.
