# Endstone BlockData Inspector Plugin

An Endstone Python wheel plugin for inspecting container NBT, mutating block states, and auditing inventory transactions in Minecraft Bedrock Edition.

## Features
- `/bd locate [radius]`: Bounding box container discovery
- `/bd inspect [x] [y] [z]`: Block NBT, runtime ID & slot inspector
- `/bd item add <slot> <id> [count] [nbt]`: Item insertion with custom NBT
- `/bd item remove <slot>`: Slot clearing via NBT removal patch
- `/bd audit <start|stop|history>`: Container transaction audit recorder
- `/bd state set <prop> <val>`: Block state mutation

## Installation
```bash
pip install endstone_blockdata_inspector-0.4.5a9-py3-none-any.whl
```
