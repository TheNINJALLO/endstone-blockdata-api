"""Verify exact native binary identities and the recorded instruction/data sites."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def verify(profile: dict, paths: dict[str, Path]) -> dict:
    checked = {}
    for image, expected in profile["images"].items():
        path = paths[image]
        with path.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
            if digest != expected["sha256"] or path.stat().st_size != expected["size_bytes"]:
                raise ValueError(f"{image} does not match the exact binary profile")
            for site in expected["sites"]:
                data = bytes.fromhex(site["bytes"])
                offset = site["file_offset"]
                if offset < 0 or offset + len(data) > expected["size_bytes"] or not data:
                    raise ValueError(f"Invalid {image} profile site: {site['address']}")
                source.seek(offset)
                if source.read(len(data)) != data:
                    raise ValueError(f"{image} fingerprint mismatch at {site['address']}")
        checked[image] = len(expected["sites"])
    return {"binary_profile_verified": True, "bds_package": profile["bds_package"],
            "endstone": profile["endstone"], "sites_checked": checked,
            "native_adapter_qualified": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--bds", required=True, type=Path)
    parser.add_argument("--endstone-runtime", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    result = verify(profile, {"BdsOffsets": args.bds, "EndstoneOffsets": args.endstone_runtime})
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
