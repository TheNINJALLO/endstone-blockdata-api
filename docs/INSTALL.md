# Install Endstone Blockdata API v0.6.5

Version: `v0.6.5`. [Download release](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/tag/v0.6.5).

Use BDS **1.26.51.1**, **Endstone 0.11.12**, and **CPython 3.14** on Linux x86-64. Stop the server, replace the previous native plugin and command wheel together with the release `.so` and matching `cp314-cp314-linux_x86_64.whl`, then restart. BDS itself does not need updating.

The complete deployment ZIP contains both plugin files. The portable API wheel alone does not install the server plugin. Windows native binaries are not included.

The published [v0.6.4 artifacts](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/tag/v0.6.4) require Endstone 0.11.11. Package metadata keeps `endstone>=0.11.11`; native version gates still require the exact runtime used to build the plugin.
