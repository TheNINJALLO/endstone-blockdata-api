# Build status

Version: **0.6.9**

Release target: Endstone **0.11.15**, Minecraft **1.26.60**,
BDS package
1.26.60.6/runtime 26.60, and CPython **3.14** on Linux x86-64.
Network protocol is **2225**.

SDK commit: `b4aaa87d2c5305e7d340168f824ac2e2ea722e44`.

Native addresses and binary guards have been refreshed. Native builds and disposable live qualification passed. Native C++ and Python test suites passed (6 CTest checks and 89 Python tests) and are recorded in `compatibility/native-qualification.json`.
See `compatibility/bds-1.26.60.json` and `compatibility/native-qualification.json`.

The package dependency remains `endstone>=0.11.11`. Private native hooks require the exact verified binary pair.

Release: [v0.6.9](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/tag/v0.6.9). Previous Endstone 0.11.12 qualification is preserved in
`compatibility/native-qualification-endstone-0.11.12.json`.

The exact packaged artifacts also passed a persisted-block restart and clean shutdown. Qualification used `enable-script=true` and no connected-player session. With `enable-script=false`, the BlockData/WorldGen test servers failed to initialize plugins and later commands caused a process exit; that configuration is not qualified.
