# Build status

Version: **0.6.4**

[Native release v0.6.4](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/tag/v0.6.4) targets Endstone 0.11.11, BDS package
1.26.51.1/runtime 26.51, and CPython 3.14 on Linux x86-64.

Pinned SDK commit: `37b395378d91d6d20f1c52bf9d79dbd20e152458`.

## Validation

Live block replacement, container name/NBT writes, inventory writes, bundle materialization/readback, shelf writes/readback, invalid-state rejection, save and shutdown.

Native C++ and Python test suites, binary identity checks, package checks, and deployment evidence accompany the release. Enchantment additionally requires ASan/UBSan and `production_ready: true` from its live production check.

Endstone package metadata accepts **>=0.11.11** with no upper bound. Native hooks require the verified BDS 1.26.51.1 / Endstone 0.11.11 binary pair; later private runtimes need separate qualification.
