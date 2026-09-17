# endstone-blockdata-api v0.6.4-alpha.1

**Source and portable API compatibility prerelease. Native server support for
Minecraft 1.26.51 is not yet available in this release.**

## Changes

- Prepare the Minecraft 1.26.51 / BDS 1.26.51.1 target using verified Linux and Windows server archives.
- Set the source command-plugin dependency to `endstone>=0.11.11`, without an upper version cap.
- Record Endstone v0.11.11 SDK commit `37b395378d91d6d20f1c52bf9d79dbd20e152458` and exact binary identities.
- Add archive inspection, version checks, and a native-qualification guard with regression tests.
- Bump source and portable Python package versions for this alpha release.

## Downloads and installation

The attached `py3-none-any.whl` is the **portable Python API**, installed with
`python -m pip install <wheel-file>`. It is not an in-game Endstone command plugin.
The source ZIP contains the tagged repository source. The target profile,
release manifest, and SHA256 checksums are included separately.

No updated server-plugin DLL/SO, live Python bridge, or in-game command wheel is
included. Native adapters must still be ported, rebuilt, and tested against
BDS 1.26.51.1. Allowing newer Endstone versions in dependency metadata does not
establish binary compatibility with future servers. `--require-native` continues
to reject this unqualified target.

The previous [v0.6.3 stable release](https://github.com/TheNINJALLO/endstone-blockdata-api/releases/tag/v0.6.3)
retains its original exact-runtime requirements and remains the latest stable release.
See [target preparation](docs/BDS_1_26_51.md) for verification commands.
