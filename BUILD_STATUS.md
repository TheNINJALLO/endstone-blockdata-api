# Build status

Version: **0.6.5**

Release target: Endstone **0.11.12**, BDS package
1.26.51.1/runtime 26.51, and CPython 3.14 on Linux x86-64.

Pinned SDK commit: `1c71186cba896c5e0bc432384a8a8e72dfb2a626`. BDS executables, archive hashes, and native BDS addresses are unchanged.

## Validation

Block replacement, canonical NBT, inventory and bundle read/write, shelf read/write, invalid-state rejection, save/resume, and shutdown.

Native C++ and Python test suites and disposable-server evidence are recorded in `compatibility/native-qualification.json`.

Endstone package metadata accepts **>=0.11.11** without an upper bound. Native hooks remain gated to the exact qualified runtime.

## Publication

Release: [v0.6.5](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/tag/v0.6.5). The previous [v0.6.4 release](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/tag/v0.6.4) and its 0.11.11 qualification remain historical records.
