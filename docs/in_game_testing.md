# In-Game Command & Inspection Suite

The repository includes a standalone Python wheel test plugin [`endstone_blockdata_inspector`](../examples/python/block_data_inspector_plugin/).

---

## 📦 Installation

```bash
pip install endstone_blockdata_inspector-0.4.5a9-py3-none-any.whl
```

---

## 🎮 Command Usage (`/bd`)

All subcommands require OP permission or `bd.admin`.

### 1. `/bd locate [radius]`
Scans a 3D bounding box around the player or coordinates and displays all container block entities.
- **Example**: `/bd locate 15`

### 2. `/bd inspect [x] [y] [z]`
Displays block runtime ID, state properties, revision counter, and full NBT inventory.
- **Example**: `/bd inspect 100 64 200`

### 3. `/bd item add <slot> <item_id> [count] [nbt_json]`
Inserts an item with custom NBT into the target slot.
- **Example**: `/bd item add 0 minecraft:diamond_sword 1 {"display":{"Name":"§6Excalibur"}}`

### 4. `/bd item remove <slot>`
Clears an item from the specified slot using an NBT removal patch.
- **Example**: `/bd item remove 0`

### 5. `/bd audit <start|stop|history>`
- `start`: Records initial container baseline.
- `stop`: Compares current state against baseline and outputs delta log.
- `history`: Shows past audit sessions.

### 6. `/bd state set <property> <value>`
Mutates block state properties in real-time.
- **Example**: `/bd state set facing south`
