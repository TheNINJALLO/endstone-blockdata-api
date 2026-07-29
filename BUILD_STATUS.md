# Build status

Version: **0.4.9**

## Implemented

- Portable C++ BlockData core and tests
- Python package and tests
- Exact BDS 1.26.33 / Endstone v0.11.6 adapter source
- Canonical container block-actor NBT and nested item data
- Native service and live Python bridge
- Deterministic native install and packaging scripts
- GitHub Actions Windows x64 and Linux x64 exact builds for BDS 1.26.33
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

Portable builds and package tooling are validated locally. Exact native binaries are compiled by the included GitHub Actions runners and still require first-load testing against the matching BDS executable before production use.

## GitHub Actions toolchain hotfix

- Linux exact builds run on Ubuntu 22.04 with Clang 18 and libc++ 18.
- Both platforms invoke `scripts/build_exact.py`, so executable-bit loss cannot cause exit code 126.
- Windows exact builds use clang-cl, lld-link, and Ninja inside the Visual Studio 2022 developer environment.
- Failed exact jobs upload CMake diagnostics for inspection.
