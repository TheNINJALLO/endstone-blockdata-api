# Build status

Version: **0.4.5-alpha.9**

## Implemented

- Portable C++ BlockData core and tests
- Python package and tests
- Exact BDS 1.26.32 / Endstone v0.11.5 adapter source
- Exact BDS 1.26.33 / Endstone v0.11.6 adapter source
- Canonical container block-actor NBT and nested item data
- Native service and live Python bridge
- Deterministic native install and packaging scripts
- GitHub Actions Windows x64 and Linux x64 exact build matrix
- Downloadable workflow artifacts on every push
- Automatic tagged GitHub Releases
- Raw plugin, ZIP package, manifest, and SHA-256 outputs

## Validation boundary

Portable builds and package tooling are validated locally. Exact native binaries are compiled by the included GitHub Actions runners and still require first-load testing against the matching BDS executable before production use.

## GitHub Actions toolchain hotfix

- Linux exact builds run on Ubuntu 24.04 with Clang 18 and libc++ 18.
- Shell scripts are invoked with `bash`, so browser uploads cannot cause exit code 126 by dropping executable permissions.
- Windows exact builds use Visual Studio 2022/MSVC x64 instead of clang-cl/Ninja.
- Failed exact jobs upload CMake diagnostics for inspection.
