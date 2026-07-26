# Installation

## Downloading an automatic build

Every GitHub push produces downloadable Windows x64 and Linux x64 artifacts for BDS 1.26.33 with Endstone 0.11.6. Open the repository's **Actions** tab, select the completed build, and download the package matching your operating system.

A tagged release such as `v0.4.5-beta.32` publishes the same files under the repository's **Releases** page.

Use the ZIP matching the server's operating system. Copy its packaged plugin from `plugins/` into Endstone's native plugin directory. Do not use it with any BDS or Endstone version other than BDS 1.26.33 / Endstone 0.11.6.

The `/bd` plugin requires Endstone's **CPython 3.14** runtime. The complete ZIP contains a platform-specific `cp314` wheel with `_endstone_blockdata_live` bundled inside it. Stop the server, remove every older BlockData inspector wheel from `plugins/` and any manually copied top-level `_endstone_blockdata_live` file from `.local`, then copy both files from the ZIP's `plugins/` directory into the server's `plugins/` directory. No `PYTHONPATH` or manual `site-packages` copy is required.

## Building locally

Linux:

```bash
./scripts/build_exact.sh 1.26.33 linux-x64
```

Windows PowerShell:

```powershell
./scripts/build_exact.ps1 -BdsBuild 1.26.33 -Platform windows-x64
```

Completed raw plugins, self-contained platform wheels, ZIP packages, and checksums are written to `dist/release/`.

At startup the native plugin verifies the exact BDS build, registers service ABI 2 as `endstone:blockdata:v2`, and logs whether canonical actor NBT, nested item NBT, and inventory access are active.

## Native build boundary

The exact adapters include Endstone's private BDS declarations and must be compiled with the matching Endstone source tag and ABI toolchain. The portable test build does not certify the native adapter. Treat the first live load as a staging test, keep a world backup, and confirm the startup capability log before allowing writes.
