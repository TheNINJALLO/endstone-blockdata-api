# BlockData API 0.6.7

The inspector wheel now includes the exact native provider and registers `blockdata_api` before dependent plugins load. This repairs wheel-only installs that left AntiGrief and other consumers without a native service. Checksums and version checks reject corrupted or mixed bundles.

Linux x86-64 only: Endstone 0.11.13, BDS 1.26.52.3, CPython 3.14. Replace old provider libraries and inspector wheels with the complete release wheel while the server is stopped. Preserve data folders; do not install the standalone `.so` alongside the bundle.
