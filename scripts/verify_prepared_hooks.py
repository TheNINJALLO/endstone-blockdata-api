#!/usr/bin/env python3
"""Verify offline BDS hook evidence without enabling a native runtime."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(manifest: dict, executable: Path) -> dict:
    expected = manifest["executable"]
    with executable.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
        size = os.fstat(stream.fileno()).st_size
        if (digest, size) != (expected["sha256"], expected["size_bytes"]):
            raise ValueError("BDS executable identity does not match the prepared hooks")
        checked = 0
        for site in manifest["sites"]:
            if site["status"] != "mapped-offline":
                continue
            data = bytes.fromhex(site["bytes"])
            offset = site["file_offset"]
            if not data or offset < 0 or offset + len(data) > size:
                raise ValueError("prepared hook file range is invalid")
            stream.seek(offset)
            if stream.read(len(data)) != data:
                raise ValueError(f"prepared hook bytes differ at {site['previous_address']}")
            checked += 1
    unresolved = [site["uses"] for site in manifest["sites"] if site["status"] != "mapped-offline"]
    return {
        "bds_package": manifest["bds_package"],
        "platform": manifest["platform"],
        "server_files_verified": True,
        "sites_checked": checked,
        "unresolved_sites": unresolved,
        "native_adapter_qualified": False,
        "native_release_ready": False,
        "remaining": manifest["qualification_required"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "compatibility/hooks-1.26.60-linux-x64.json")
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--require-native", action="store_true")
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        report = verify(manifest, args.executable)
        text = json.dumps(report, indent=2) + "\n"
        if args.output:
            args.output.write_text(text, encoding="utf-8")
        print(text, end="")
        if args.require_native or (args.require_complete and report["unresolved_sites"]):
            return 2
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Prepared hook verification failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
