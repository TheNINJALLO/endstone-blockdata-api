# BlockData API 0.6.10: Endstone 0.11.16 update

This source update targets Endstone **0.11.16**, BDS **1.26.65.1**, runtime **26.65**, protocol **2225** and **CPython 3.14**. Native adapters require this exact binary pair. The public Python dependency remains `endstone>=0.11.11`; it does not relax the native runtime checks.

The BDS archives match EndstoneMC/bedrock-server-data checksums. Native function mappings were checked against the exact Linux executable and Endstone runtime using symbols, RTTI, relocations and instruction sequences. The previous profiles remain available for the previous release.

This candidate must pass the branch build and disposable-server checks before native artifacts are recommended for installation. `compatibility/bds-1.26.65.json` and `SOURCE_RELEASE.json` record the pending qualification. Build artifacts are available from the update branch workflow after a successful run; no new public release has been published by this update.

Use the repository build scripts with the pinned Endstone SDK commit `23cb5758bdc070888cb89ecd1541ef25c4305b5c` and CPython 3.14. Install the native provider and its matching command/partner wheel together on a disposable server, then run the documented feature, persistence, restart and clean-shutdown checks. Retain the previous wheel, plugin and data backup together for rollback.
