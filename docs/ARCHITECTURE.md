# Architecture

`BlockDataService` is stable API. `IBlockAdapter` is the only layer allowed to touch a live Endstone/BDS world.

1. Capture occurs on the server thread.
2. A detached `BlockSnapshot` may move to workers.
3. Workers produce `BlockPatch` objects only.
4. Apply occurs on the server thread and validates `expected_revision`.
5. A native adapter marks block actors dirty and updates clients after a successful commit.

This keeps worker threads away from live `Block`, `Dimension`, `LevelChunk`, inventory and `BlockActor` objects.
