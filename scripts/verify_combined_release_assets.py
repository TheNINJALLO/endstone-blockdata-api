#!/usr/bin/env python3
"""Verify the exact cross-platform asset set before publishing a release."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


WHEEL_PREFIXES = {
    "endstone-blockdata-api": "endstone_blockdata_inspector",
    "endstone-worldgen-api": "endstone_worldgen_studio",
}
VERSION_PATTERN = re.compile(
    r"(\d+\.\d+\.\d+)(?:-(alpha|beta|rc)\.(\d+))?"
)


def pep440_version(release: str) -> str:
    match = VERSION_PATTERN.fullmatch(release)
    if match is None:
        raise SystemExit(f"Unsupported release version: {release!r}")
    base, phase, serial = match.groups()
    if phase is None:
        return base
    marker = {"alpha": "a", "beta": "b", "rc": "rc"}[phase]
    return f"{base}{marker}{serial}"


def expected_assets(slug: str, release: str, bds: str) -> set[str]:
    try:
        wheel_prefix = WHEEL_PREFIXES[slug]
    except KeyError as exc:
        raise SystemExit(f"Unsupported project slug: {slug!r}") from exc
    wheel_version = pep440_version(release)
    stem = f"{slug}-v{release}-bds-{bds}"
    return {
        f"{stem}-linux-x64.so",
        f"{stem}-linux-x64.zip",
        f"{stem}-linux-x64.sha256",
        f"{stem}-windows-x64.dll",
        f"{stem}-windows-x64.zip",
        f"{stem}-windows-x64.sha256",
        f"{wheel_prefix}-{wheel_version}-cp314-cp314-linux_x86_64.whl",
        f"{wheel_prefix}-{wheel_version}-cp314-cp314-win_amd64.whl",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the complete Linux and Windows GitHub Release input set."
    )
    parser.add_argument("--slug", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--bds", required=True)
    parser.add_argument("--release-dir", type=Path, required=True)
    args = parser.parse_args()

    expected = expected_assets(args.slug, args.version, args.bds)
    entries = list(args.release_dir.iterdir()) if args.release_dir.is_dir() else []
    non_files = sorted(path.name for path in entries if not path.is_file())
    actual = {path.name: path.stat().st_size for path in entries if path.is_file()}
    missing = sorted(expected - set(actual))
    extra = sorted(set(actual) - expected)
    if non_files or missing or extra:
        raise SystemExit(
            "Release asset set mismatch: "
            f"missing={missing}, extra={extra}, non_files={non_files}"
        )
    empty = sorted(name for name, size in actual.items() if size <= 0)
    if empty:
        raise SystemExit(f"Release assets are empty: {empty}")

    print(f"Verified {len(actual)} pre-checksum release assets for {args.slug} {args.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
