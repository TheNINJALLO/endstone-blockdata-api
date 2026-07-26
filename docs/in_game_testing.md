# In-game command and inspection suite

The release includes the `endstone_blockdata_inspector` test-plugin wheel.

## Install

1. Install the exact native BlockData bundle for the server's BDS build and platform.
2. Ensure the bundle's `_endstone_blockdata_live` module is importable by Endstone.
3. Copy `endstone_blockdata_inspector-0.4.5b30-py3-none-any.whl` to `plugins/`.
4. Restart Endstone and confirm both the native API and inspector load.

The wheel registers Endstone entry point `blockdata-inspector`, command `/bd`
(alias `/blockdata`), and permission `bd.admin` with operator default.

## Commands

### `/bd locate [radius]`

Captures a live region and lists nearby container actors. Radius is capped at 12.

### `/bd inspect [x y z]`

Displays the live block runtime ID, states, revision, actor NBT, and inventory.

### `/bd item add <slot> <item_id> [count] [nbt_json]`

Writes a live item through the native bridge. Example:

```text
/bd item add 0 minecraft:diamond_sword 1 {"display":{"Name":"Excalibur"}}
```

### `/bd item remove <slot>`

Clears the selected live inventory slot.

### `/bd audit <start|stop|history> [x y z]`

Stores and compares live snapshots, reporting block, actor-NBT, and slot changes.

### `/bd state set <property> <value> [x y z]`

Writes a live block-state property through the native bridge.

Every command checks native service availability and adapter capabilities first.
Missing live support is reported as an error; the plugin never substitutes the
in-memory reference implementation.
