#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PROJECTS = {
    "blockdata": {
        "slug": "endstone-blockdata-api",
        "plugin_prefix": "endstone_blockdata_bds_",
    },
    "worldgen": {
        "slug": "endstone-worldgen-api",
        "plugin_prefix": "endstone_worldgen_bds_",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package exact Endstone plugin build outputs.")
    parser.add_argument("--project", choices=PROJECTS, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--bds", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--release-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    info = PROJECTS[args.project]
    stage = args.stage.resolve()
    release_dir = args.release_dir.resolve()
    if not stage.is_dir():
        raise SystemExit(f"Install stage does not exist: {stage}")

    suffixes = (".dll", ".so", ".dylib")
    candidates = [
        path
        for path in stage.rglob("*")
        if path.is_file()
        and path.suffix.lower() in suffixes
        and info["plugin_prefix"] in path.name
    ]
    if len(candidates) != 1:
        names = ", ".join(str(path) for path in candidates) or "none"
        raise SystemExit(f"Expected exactly one packaged plugin, found {len(candidates)}: {names}")

    plugin = candidates[0]
    release_dir.mkdir(parents=True, exist_ok=True)
    release_stem = f"{info['slug']}-v{args.version}-bds-{args.bds}-{args.platform}"
    raw_plugin = release_dir / f"{release_stem}{plugin.suffix.lower()}"
    shutil.copy2(plugin, raw_plugin)

    files = []
    for path in sorted(stage.rglob("*")):
        if path.is_file():
            files.append(
                {
                    "path": path.relative_to(stage).as_posix(),
                    "size": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )

    manifest = {
        "schema": 1,
        "project": info["slug"],
        "version": args.version,
        "bds": args.bds,
        "platform": args.platform,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "primary_plugin": plugin.relative_to(stage).as_posix(),
        "files": files,
    }
    manifest_path = stage / "PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    archive = release_dir / f"{release_stem}.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=f"{release_stem}/{path.relative_to(stage).as_posix()}")

    checksums = release_dir / f"{release_stem}.sha256"
    checksums.write_text(
        f"{sha256(raw_plugin)}  {raw_plugin.name}\n{sha256(archive)}  {archive.name}\n",
        encoding="utf-8",
    )

    print(raw_plugin)
    print(archive)
    print(checksums)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - command-line safety net
        print(f"packaging failed: {exc}", file=sys.stderr)
        raise
