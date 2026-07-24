# Validation results

Validated on 2026-07-22:

- Portable CMake configuration and C++20 build
- CTest BlockData suite
- Python unit tests
- GitHub Actions YAML parsing
- Release packaging script with synthetic Linux and Windows plugin stages
- ZIP integrity and package-manifest validation
- Stable release filenames for both supported BDS versions and platforms
- Source ZIP integrity

Not validated in this environment:

- Loading the exact native `.dll` or `.so` inside BDS 1.26.32 or 1.26.33
- Live container mutation against a production world
