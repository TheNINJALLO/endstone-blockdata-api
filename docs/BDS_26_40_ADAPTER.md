# Exact Bedrock 26.40 BlockActor NBT adapter

| BDS build | Endstone tag | Runtime result |
|---|---|---|
| 1.26.40 | v0.11.7 | accepted |
| 1.26.40 with any other Endstone version | mismatch | refused; public adapter only |
| anything else | none | refused |

The native entry points and instruction fingerprints were verified against the
official `1.26.40.8` Linux and Windows server executables. The source-release
metadata records the exact archive URLs and SHA-256 checksums. The downloaded
server archives are not redistributed by this project.

## Capture path

1. Resolve Endstone's exact dimension implementation.
2. Obtain the matching BDS `BlockSource`.
3. Locate the live `BlockActor` at the requested position.
4. Obtain `IVanillaMainBlockActorComponent` and, where present, `Container`.
5. Build a recursive canonical actor compound containing:
   - `id`, `x`, `y`, `z`
   - actor type/build metadata
   - `CustomName`
   - `Container::addAdditionalSaveData` output
   - complete `Items` list
6. For each item, include its nested user-data compound and placement/destroy restrictions.
7. Hash the complete snapshot for conflict and anti-grief auditing.

## Apply path

Supported changes are applied on the Endstone primary thread through typed BDS interfaces. A scoped native bridge supplies the active `Level` item registry while item stacks are validated and copied; placement and destroy restrictions are resolved completely before either list is committed. The adapter validates the resulting actor data, calls `setChanged`, notifies the main `BlockSource`, and fires the block-entity update.

## Service access

Native plugins compiled for service ABI 2 load `endstone:blockdata:v2` through Endstone's `ServiceManager`. Python plugins use the matching companion `_endstone_blockdata_live` extension and pass their `self.server` object. The versioned name makes mixed native-plugin/bridge releases fail lookup safely.

## Build

Linux requires the same Clang/libc++ environment as Endstone:

```bash
./scripts/build_exact.sh 1.26.40
```

Windows requires clang-cl, CMake 3.29+ and Ninja:

```powershell
./scripts/build_exact.ps1 -BdsBuild 1.26.40
```

Only BDS `1.26.40` with Endstone `v0.11.7` is supported. Back up the world before enabling native writes.
