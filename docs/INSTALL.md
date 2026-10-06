# Install Endstone BlockData API v0.6.7

Version: `v0.6.7`. [Download release](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/tag/v0.6.7).

Use BDS **1.26.52.3**, **Endstone 0.11.13**, and **CPython 3.14** on Linux x86-64.

Stop the server. Replace old inspector wheels and native BlockData libraries with `endstone_blockdata_inspector-0.6.7-cp314-cp314-linux_x86_64.whl` in `plugins/`, then restart. Preserve plugin data folders. The wheel now contains both the bridge and its matching native provider, verifies its checksum, and registers `blockdata_api` automatically before dependent plugins load.

The deployment ZIP contains this same complete wheel. The standalone `.so` is available for advanced/manual deployments; do not add it alongside the complete wheel. The portable Python SDK alone does not install the server plugin. Windows native binaries are not included. Mixed versions are rejected before a bridge/native call.
