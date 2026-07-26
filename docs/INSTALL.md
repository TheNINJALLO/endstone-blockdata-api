# Installation

## Downloading an automatic build

Every GitHub push produces downloadable Windows x64 and Linux x64 artifacts for BDS 1.26.33 with Endstone 0.11.6. Open the repository's **Actions** tab, select the completed build, and download the package matching your operating system.

A tagged release such as `v0.4.5-beta.30` publishes the same files under the repository's **Releases** page.

Use the ZIP matching the server's operating system. Copy its packaged plugin from `plugins/` into Endstone's native plugin directory. Do not use it with any BDS or Endstone version other than BDS 1.26.33 / Endstone 0.11.6.

The `/bd` test wheel requires an Endstone host running **CPython 3.14**, and the exact bundle's native bridge must carry the matching `cp314`/`cpython-314` ABI tag. Make the extracted ZIP's `python/` directory importable by that interpreter (set `PYTHONPATH` to it, or copy its contents into Endstone's Python `site-packages`), then put `endstone_blockdata_inspector-0.4.5b30-py3-none-any.whl` in the server's `plugins/` directory. Installing only the raw `.dll`/`.so` and the wheel omits `_endstone_blockdata_live`, so live commands cannot run.

## Building locally

Linux:

```bash
./scripts/build_exact.sh 1.26.33 linux-x64
```

Windows PowerShell:

```powershell
./scripts/build_exact.ps1 -BdsBuild 1.26.33 -Platform windows-x64
```

Completed raw plugins, ZIP packages, and checksums are written to `dist/release/`.

At startup the native plugin verifies the exact BDS build, registers `endstone:blockdata`, and logs whether canonical actor NBT, nested item NBT, and inventory access are active.

## Native build boundary

The exact adapters include Endstone's private BDS declarations and must be compiled with the matching Endstone source tag and ABI toolchain. The portable test build does not certify the native adapter. Treat the first live load as a staging test, keep a world backup, and confirm the startup capability log before allowing writes.
