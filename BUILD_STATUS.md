# Build status

Version: **0.6.7**

Release target: Endstone **0.11.13**, Minecraft **1.26.52**,
BDS package
1.26.52.3/runtime 26.52, and CPython **3.14** on Linux x86-64.
Network protocol remains **2193**.

SDK commit: `3491c609ddfde392cee2b062e3063e39aae87274`.

Native addresses and binary guards have been refreshed. Native builds and disposable live qualification passed. Native C++ and Python test suites passed (6 CTest checks and 85 Python tests) and are recorded in `compatibility/native-qualification.json`.
See `compatibility/bds-1.26.52.json` and `compatibility/native-qualification.json`.

The package dependency remains `endstone>=0.11.11`. Private native hooks require the exact verified binary pair.

Release: [v0.6.7](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/tag/v0.6.7). Previous Endstone 0.11.12 qualification is preserved in
`compatibility/native-qualification-endstone-0.11.12.json`.
