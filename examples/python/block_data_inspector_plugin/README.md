# Endstone BlockData Inspector Plugin

An Endstone 0.11 Python wheel that exercises the **live** `endstone:blockdata:v2`
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
endstone_blockdata_inspector-0.4.7-cp314-cp314-linux_x86_64.whl
endstone_blockdata_inspector-0.4.7-cp314-cp314-win_amd64.whl
```

Endstone discovers the `blockdata-inspector` entry point at startup. All
commands require operator status or the `bd.admin` permission.

## Commands

- `/bd` (alias `/blockdata`) or `/bd menu`: open the guarded player menu; the
  console receives text help.
- `/bd locate [radius]`: list supported containers, their capacity, occupied
  slots, and item previews; select the nearest result.
- `/bd inspect`: inspect the selected container.
- `/bd inspect <x> <y> <z>`: inspect an absolute block position and select it
  when it is a supported container. Canonical NBT is capped to a 768-character
  preview with the complete character count and a clear truncation marker;
  occupied items are summarized separately.
- `/bd item add <slot> <id> [count] [nbt]`: write a slot in the selected
  container.
- `/bd item add at <x> <y> <z> <slot> <id> [count] [nbt]`: write a slot at an
  explicit absolute position.
- `/bd item remove <slot>`: clear a slot in the selected container.
- `/bd item remove at <x> <y> <z> <slot>`: clear a slot at an explicit position.
- `/bd audit <start|stop> [x y z]`: compare snapshots at an explicit position
  or at the selected container when coordinates are omitted.
- `/bd audit history`: show recent audit sessions.
- `/bd state set <property> <value> [x y z]`: write a live block state at an
  explicit position or at the selected container.

Commands never infer a mutation target from the block under the player. Run
`/bd locate` or `/bd inspect <x> <y> <z>` first, or use one of the explicit
coordinate forms. Coordinates are three absolute integers; partial or malformed
coordinates are rejected.

Only one BlockData form can be active per player. Closing a child page returns
to its parent, and item or state writes require a separate confirmation. Form
inputs are validated before dispatch; stale callbacks, permission loss,
disconnect, death, plugin shutdown, and form-send failures cannot retain a lock
or repeat an action.

The plugin reports a clear in-game error when the native service, bridge, or a
required adapter capability is unavailable. Mutation commands require a bridge
that exposes native `apply`; they never report success for an in-memory change.
Container discovery uses the native `is_container` and `container_size` fields,
and reports container-looking blocks with missing actor capture separately.
