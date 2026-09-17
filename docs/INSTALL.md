# Install Endstone BlockData API v0.6.4

Release tag: `v0.6.4`.

Download the Linux x86-64 assets from [v0.6.4](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/tag/v0.6.4). Stop the server, remove the older plugin and command wheel, and copy the new `.so` plus its matching `cp314-cp314-linux_x86_64.whl` into `plugins/`. Start BDS 1.26.51.1 with Endstone 0.11.11.

Linux x86-64 native release for Minecraft **1.26.51**, BDS **1.26.51.1**, and Endstone **0.11.11**, with matching CPython **3.14** command wheels.

Endstone package metadata accepts **>=0.11.11** with no upper bound. Native hooks require the verified BDS 1.26.51.1 / Endstone 0.11.11 binary pair; later private runtimes need separate qualification.

The complete deployment ZIP includes both plugin files. The portable Python API wheel alone does not install the native server plugin. Windows native binaries are not included in this release.
