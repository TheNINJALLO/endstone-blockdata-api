# Endstone BlockData Inspector Plugin

An Endstone 0.11 Python wheel that exercises the **live** `endstone:blockdata`
native service. It never falls back to the in-memory reference adapter.

## Installation

Install the complete native BlockData package matching the server's exact
operating system and BDS build, then use its matching platform-specific command
wheel. That wheel contains `_endstone_blockdata_live` inside the inspector
package, so the bridge does not depend on the bundle's `python/` directory being
on `sys.path`. The Endstone host must run **CPython 3.14** to match the native
bridge ABI. Top-level bridge modules from older releases are deliberately
ignored so they cannot hide a missing or corrupt bridge in the installed wheel.

```text
endstone_blockdata_inspector-0.4.5b31-cp314-cp314-linux_x86_64.whl
endstone_blockdata_inspector-0.4.5b31-cp314-cp314-win_amd64.whl
```

Endstone discovers the `blockdata-inspector` entry point at startup. All
commands require operator status or the `bd.admin` permission.

## Commands

- `/bd` (alias `/blockdata`): show help.
- `/bd locate [radius]`: query native region capture for nearby containers.
- `/bd inspect [x y z]`: inspect live runtime ID, states, actor NBT, and slots.
- `/bd item add <slot> <id> [count] [nbt]`: write a live inventory slot.
- `/bd item remove <slot>`: clear a live inventory slot.
- `/bd audit <start|stop|history> [x y z]`: compare two live snapshots.
- `/bd state set <property> <value> [x y z]`: write a live block state.

The plugin reports a clear in-game error when the native service, bridge, or a
required adapter capability is unavailable. Mutation commands require a bridge
that exposes native `apply`; they never report success for an in-memory change.
