# Validation results

Validated on 2026-07-25:

- Portable MSVC Release configuration and C++20 build
- CTest BlockData suite (3/3)
- Python unit and release-tool tests (15/15)
- Built test wheel inspection against Endstone 0.11.6, including its entry point,
  native-plugin dependency, commands, permissions, CPython 3.12 requirement,
  plugin construction, and packaged contents
- Project/version/dependency metadata consistency for `0.4.5-beta.29`
- GitHub Actions YAML parsing
- Release packaging round-trip with a synthetic Windows plugin stage
- Checksum, ZIP path, manifest, native bridge, unresolved Bedrock symbol,
  CPython 3.12 SOABI, dynamic runtime dependency, and non-relocatable RPATH
  rejection gates
- Stable release filenames for BDS 1.26.32 and 1.26.33 on Linux and Windows
- Source ZIP integrity and `git diff --check`

Not validated in this environment:

- Exact Endstone/Bedrock native builds from the GitHub Actions Linux and Windows
  matrix
- Loading the exact native `.dll` or `.so` inside BDS 1.26.32 or 1.26.33
- Live container mutation against a production world
