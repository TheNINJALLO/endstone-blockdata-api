# Endstone BlockData API

> **CI update required:** If GitHub still shows `Portable tests (ubuntu-22.04)`, it is running the old hidden workflow. Follow [`APPLY_CI_FIX.md`](APPLY_CI_FIX.md).


A version-gated live block, block-state, block-actor and container-NBT service for Endstone.

## Exact Minecraft Bedrock 26.30-family support

- BDS 1.26.32 with Endstone v0.11.5
- BDS 1.26.33 with Endstone v0.11.6

The native adapter refuses every other runtime build.

## What v0.4.5-alpha.9 exposes

- Live block type, runtime ID and state permutations.
- Live `BlockActor` lookup through the matching BDS `BlockSource`.
- A structured canonical block-actor NBT tree.
- Container additional-save data.
- Every container slot, including item name, count, damage, aux value and legacy ID.
- Complete nested item `tag` compounds, including enchantments, lore and custom data.
- `CanPlaceOn` and `CanDestroy` lists.
- Container custom names and supported NBT/inventory writes.
- Dirty marking, validation and client block-actor updates.
- Snapshot revisions and inventory-level audit diffs for anti-grief systems.
- Native Endstone service name: `endstone:blockdata`.
- Live Python bridge module: `_endstone_blockdata_live`.


## Automatic GitHub builds

Every push and pull request builds and tests the portable core, then compiles exact native packages for Windows x64 and Linux x64 against both supported BDS builds. The completed `.dll`, `.so`, ZIP package, and per-package SHA-256 file are available from the workflow run's **Artifacts** section for 30 days.

Pushing the exact tag `v0.4.5-alpha.9` also creates or updates a GitHub Release and attaches all four platform/BDS packages plus combined checksums. See `docs/GITHUB_RELEASES.md`.

## C++ consumer

```cpp
#include <endstone_blockdata/live_service.h>

auto api = server.getServiceManager().load<endstone_blockdata::LiveBlockDataService>(
    std::string(endstone_blockdata::BlockDataServiceName));

auto chest = api->capture({"overworld", 100, 64, 200});
```

See `examples/cpp/antigrief_container_reactor.cpp`.

`ContainerAuditReactor` is included as a reusable before/after snapshot unit. It records detached block-actor/container NBT and returns per-slot additions, removals, replacements, count changes, and nested-tag changes.

## Python consumer

```python
from _endstone_blockdata_live import capture

snapshot = capture(self.server, "overworld", 100, 64, 200)
items = snapshot["block_entity"]["inventory"]
actor_nbt = snapshot["block_entity"]["nbt"]
```

See `examples/python/live_antigrief_capture.py`.

## NBT boundary

The adapter produces the complete canonical NBT needed to inspect and audit supported containers. It does not claim an unverified byte-identical call to Mojang's hidden general `BlockActor::save/load` ABI. Identity fields and adapter metadata are read-only, while container fields are applied through the exact typed BDS interfaces.

See `docs/BDS_26_30_ADAPTER.md`.
