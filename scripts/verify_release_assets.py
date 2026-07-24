#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from zipfile import ZipFile


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify packaged Endstone release assets.")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--bds", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--release-dir", type=Path, default=Path("dist/release"))
    args = parser.parse_args()

    stem = f"{args.slug}-v{args.version}-bds-{args.bds}-{args.platform}"
    expected_suffix = ".dll" if args.platform.startswith("windows") else ".so"
    raw = args.release_dir / f"{stem}{expected_suffix}"
    archive = args.release_dir / f"{stem}.zip"
    checksums = args.release_dir / f"{stem}.sha256"

    for path in (raw, archive, checksums):
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"Missing or empty release asset: {path}")

    with ZipFile(archive) as zf:
        bad = zf.testzip()
        if bad:
            raise SystemExit(f"Corrupt ZIP member: {bad}")
        manifests = [name for name in zf.namelist() if name.endswith("/PACKAGE_MANIFEST.json")]
        if len(manifests) != 1:
            raise SystemExit(f"Expected one PACKAGE_MANIFEST.json, found {len(manifests)}")
        manifest = json.loads(zf.read(manifests[0]))

    expected = {
        "project": args.slug,
        "version": args.version,
        "bds": args.bds,
        "platform": args.platform,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise SystemExit(f"Manifest mismatch for {key}: expected {value}, got {manifest.get(key)}")

    print(f"Verified {raw.name}")
    print(f"Verified {archive.name}")
    print(f"Verified {checksums.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
