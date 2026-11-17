Targets **Endstone 0.11.16**, **BDS 1.26.65.1 / runtime 26.65**, protocol **2225**, and **Python 3.14** on Linux x86-64.

Install the complete `endstone_blockdata_inspector-0.6.10-cp314-cp314-linux_x86_64.whl` in `plugins/`. It contains the matching native provider and loads it before dependent plugins. Replace old inspector wheels/loose BlockData providers while stopped; preserve plugin data.

This release refreshes exact native addresses, binary guards and SDK pins. It also fixes saved container names and canonical name capture after restart. Portable C++, 89 Python tests, relocated-wheel/service checks, real block/container/item/bundle writes, stale revision rejection, full restart persistence and clean shutdown passed. `QUALIFICATION.json` binds the live-tested wheel to its SHA-256.

Windows native binaries and connected-player behavior are outside this release's qualification. Qualification used `enable-script=true`.
