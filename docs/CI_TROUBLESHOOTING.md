# GitHub Actions troubleshooting

## Fixed in 0.4.5-alpha.9

The original exact-build workflow could fail with:

- Linux exit code `126`, because GitHub's browser upload did not retain the executable bit on `scripts/build_exact.sh`.
- Windows exit code `1`, because the workflow forced `clang-cl` and Ninja instead of Endstone's Visual Studio/MSVC build path.

The workflow now calls the Linux script as `bash scripts/build_exact.sh`, uses Clang 18 with libc++ 18 on Ubuntu 24.04, and uses Visual Studio 2022/MSVC on Windows.

## Reading a failed build

If an exact job still fails, open the workflow run and download the artifact whose name begins with:

```text
endstone-blockdata-api-diagnostics-
```

It contains the CMake cache and available configure/build logs. This makes adapter-source failures visible instead of ending with only a generic exit code.
