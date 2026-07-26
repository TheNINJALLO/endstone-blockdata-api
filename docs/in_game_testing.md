# In-game command and inspection suite

The release includes the `endstone_blockdata_inspector` test-plugin wheel.

## Install

1. Stop the server and remove every older BlockData inspector wheel from `plugins/`.
2. Remove any manually copied top-level `_endstone_blockdata_live` file from `plugins/.local`.
3. Extract the BDS 1.26.33 ZIP matching the server platform and copy both files from its `plugins/` directory into the server's `plugins/` directory.
4. Restart Endstone and confirm both the native API and inspector load.

The wheel registers Endstone entry point `blockdata-inspector`, command `/bd`
(alias `/blockdata`), and permission `bd.admin` with operator default.

## Commands

### `/bd locate [radius]`

Captures a live region, filters for native `is_container` actors, and lists each
container's capacity, occupied count, and up to three item previews. Radius is
capped at 12. The nearest result becomes that sender's active container target.
Container-looking blocks whose actor or container component could not be
captured are reported separately with their native capture status.

### `/bd inspect`

Inspects the active container target. Run `/bd locate` or an explicit inspect
first. Only occupied contents are printed, together with total capacity.

### `/bd inspect <x> <y> <z>`

Displays the live block runtime ID, states, revision, actor NBT, container
capacity, and occupied contents at an absolute position. A successfully captured
container becomes the sender's active target. Canonical NBT is rendered as a
maximum 768-character preview with its full character count and an explicit
`TRUNCATED` marker when the complete JSON is larger; occupied inventory remains
available in the separate bounded contents summary.

### `/bd item add <slot> <item_id> [count] [nbt_json]`

Writes a live item through the native bridge. Example:

```text
/bd item add 0 minecraft:diamond_sword 1 {"display":{"Name":"Excalibur"}}
```

The no-coordinate form uses the active container target. To address a container
directly, use:

```text
/bd item add at <x> <y> <z> <slot> <item_id> [count] [nbt_json]
```

### `/bd item remove <slot>`

Clears the selected live inventory slot.

Use `/bd item remove at <x> <y> <z> <slot>` to clear a slot at an explicit
absolute position.

### `/bd audit <start|stop> [x y z]`

Stores and compares live snapshots, reporting block, actor-NBT, and slot changes.
Without coordinates it uses the sender's active container target. Empty-slot
markers are normalized away so empty-to-item and item-to-empty changes are
reported as added and removed.

### `/bd audit history`

Displays the five most recent audit sessions. This form does not accept a
position.

### `/bd state set <property> <value> [x y z]`

Writes a live block-state property through the native bridge.

Without coordinates this uses the active container target. With coordinates it
uses exactly three absolute integers.

No mutating command silently falls back to the block under the player. Partial,
relative, or malformed coordinates are rejected; select a target first or use a
complete explicit-position form.

Every command checks native service availability and adapter capabilities first.
Missing live support is reported as an error; the plugin never substitutes the
in-memory reference implementation.
