> Historical offline preparation from 2026-10-27. The 2026-10-28 release now targets Endstone 0.11.15 / BDS 1.26.60.6 (protocol 2225). See `compatibility/bds-1.26.60.json` for current qualification. These inert preparation tables and discovery manifests remain historical candidate evidence; several candidates were corrected during the native port.

# BDS 1.26.60.6 preparation

Local branch: `native/bds-1.26.60-preparation`. Unpublished; no release version bump.

The official Linux and Windows archives and executable SHA-256 identities are
recorded in [the pending profile](compatibility/bds-1.26.60.json).
Offline mapping: **6/6 Linux storage entry points**. The [Linux hook manifest](compatibility/hooks-1.26.60-linux-x64.json)
records address-discovery evidence and executable bytes. These records do not
establish native ABI compatibility.

Storage fingerprints and lifetime helpers are staged. Recheck native container, tracker, and item layouts against the matching SDK.

The C++ preparation table is inert and is not included by the active adapters.
It declares `RuntimeQualified = false` and `ReleaseReady = false`; unresolved
addresses use `std::nullopt`. Existing build defaults and release profiles remain
on BDS 1.26.52 / Endstone 0.11.14.

## Verify the downloaded server

From this repository, with the archive downloaded beside the four projects:

```text
python scripts/prepare_bds_target.py --target compatibility/bds-1.26.60.json --platform linux-x64 --archive ../.build-inputs/bds-1.26.60-preparation/bedrock-server-linux-x64-1.26.60.6.zip
python scripts/verify_prepared_hooks.py --executable ../.build-inputs/bds-1.26.60-preparation/linux-x64/bedrock_server
```

Append `--require-native` to either command to enforce the pending native gate:
it must exit 2. `verify_prepared_hooks.py --require-complete` also exits 2 while
any BDS hook still requires a port. Successful offline byte verification alone
never permits native qualification.

## When the matching Endstone build is available

Record its actual SDK commit, release version, Python ABI, and runtime binary
identities. Recheck changed BDS layouts and call contracts; fill any unset BDS
addresses. Relocate and fingerprint private Endstone entry points using that
actual runtime. Rebuild the native plugin and Python bridge together, then run
disposable-server gameplay, persistence, restart, and clean-shutdown regressions.
Update qualification evidence before enabling a new target. Publishing still
requires a separate release instruction.
