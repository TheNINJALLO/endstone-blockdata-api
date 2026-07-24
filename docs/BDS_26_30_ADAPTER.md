# Exact Bedrock 26.30 BlockActor NBT adapter

| BDS build | Endstone tag | Runtime result |
|---|---|---|
| 1.26.32 | v0.11.5 | accepted |
| 1.26.33 | v0.11.6 | accepted |
| anything else | none | refused |

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

Supported changes are applied on the Endstone primary thread through typed BDS interfaces. The adapter validates the resulting actor data, calls `setChanged`, notifies the main `BlockSource`, and fires the block-entity update.

## Service access

Native plugins load `endstone:blockdata` through Endstone's `ServiceManager`. Python plugins use the companion `_endstone_blockdata_live` extension and pass their `self.server` object.

## Build

Linux requires the same Clang/libc++ environment as Endstone:

```bash
./scripts/build_exact.sh 1.26.33
```

Windows requires clang-cl, CMake 3.29+ and Ninja:

```powershell
./scripts/build_exact.ps1 -BdsBuild 1.26.33
```

Use `1.26.32` for Endstone v0.11.5. Back up the world before enabling native writes.
