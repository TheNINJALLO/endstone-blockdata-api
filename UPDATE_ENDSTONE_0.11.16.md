# BlockData API 0.6.10: Endstone 0.11.16 update

This source update targets Endstone **0.11.16**, BDS **1.26.65.1**, runtime **26.65**, protocol **2225** and **CPython 3.14**. Native adapters require this exact binary pair. The public Python dependency remains `endstone>=0.11.11`; it does not relax the native runtime checks.

The BDS archives match EndstoneMC/bedrock-server-data checksums. Native function mappings were checked against the exact Linux executable and Endstone runtime using symbols, RTTI, relocations and instruction sequences. The previous profiles remain available for the previous release.

The Linux exact native build and complete-wheel disposable-server checks passed. `compatibility/bds-1.26.65.json` and `SOURCE_RELEASE.json` link the artifact hashes, live write results, full restart persistence and clean shutdown. The update fixes native name persistence by updating both name fields the native save-policy flag, and the canonical name capture path. The stable artifacts are available from the release page. Windows native binaries remain unqualified, and no connected client was used.

Use the repository build scripts with the pinned Endstone SDK commit `23cb5758bdc070888cb89ecd1541ef25c4305b5c` and CPython 3.14. Install the complete inspector wheel, which includes its matching native provider on a disposable server, then run the documented feature, persistence, restart and clean-shutdown checks. Retain the previous wheel, plugin and data backup together for rollback.
