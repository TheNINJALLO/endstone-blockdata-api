# Endstone BlockData Inspector Plugin

An Endstone 0.11 Python wheel that exercises the **live** `endstone:blockdata`
native service. It never falls back to the in-memory reference adapter.

## Installation

Install the native BlockData package matching the server's exact operating
system and BDS build first. Its `_endstone_blockdata_live` module must be on the
Endstone Python path, and the Endstone host must run **CPython 3.12** to match
the native bridge ABI. Then copy this wheel into the server's `plugins/` folder:

```text
endstone_blockdata_inspector-0.4.5b29-py3-none-any.whl
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
