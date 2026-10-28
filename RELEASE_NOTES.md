# v0.6.9 - Minecraft 26.60 / Endstone 0.11.15

Target BDS **1.26.60.6**, runtime **26.60**, protocol **2225**, and CPython **3.14** on Linux x86-64. The exact SDK is pinned to `b4aaa87d2c5305e7d340168f824ac2e2ea722e44`. Native binaries and matching wheels passed automated live checks, saved-block restart, and clean shutdown. See `compatibility/native-qualification.json` for artifact hashes and test scope.

Use the default `enable-script=true`. The disabled-scripting configuration and Windows native API packages are unqualified. No connected-player session was used for this update. Historical notes follow.

---

# BlockData API 0.6.8

The inspector wheel now includes the exact native provider and registers `blockdata_api` before dependent plugins load. This repairs wheel-only installs that left AntiGrief and other consumers without a native service. Checksums and version checks reject corrupted or mixed bundles.

Linux x86-64 only: Endstone 0.11.14, BDS 1.26.52.3, CPython 3.14. Replace old provider libraries and inspector wheels with the complete release wheel while the server is stopped. Preserve data folders; do not install the standalone `.so` alongside the bundle.
