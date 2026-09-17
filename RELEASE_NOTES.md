# Endstone BlockData API v0.6.4

Linux x86-64 native release for Minecraft **1.26.51**, BDS **1.26.51.1**, and Endstone **0.11.11**, with matching CPython **3.14** command wheels.

Endstone package metadata accepts **>=0.11.11** with no upper bound. Native hooks require the verified BDS 1.26.51.1 / Endstone 0.11.11 binary pair; later private runtimes need separate qualification.

Includes the native Linux `.so`, matching command wheel, deployment archive, source/SDK assets, and SHA-256 checksums.

Verified against the supplied server files using isolated live servers, native C++ tests, Python tests, exact binary guards, and clean shutdown checks. See `compatibility/native-qualification.json` for retained live evidence. No server binaries are redistributed.
