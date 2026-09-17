#!/usr/bin/env python3
"""Verify a supplied BDS archive and prepare a future Endstone build target.

This command only reads server files. Archive verification does not qualify
private Bedrock or Endstone ABI layouts for use by a native adapter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
import zipfile
from pathlib import Path
from typing import BinaryIO

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = ROOT / "compatibility" / "bds-1.26.51.json"


def fingerprint(stream: BinaryIO) -> dict:
    digest = hashlib.sha256()
    size = 0
    while chunk := stream.read(1024 * 1024):
        digest.update(chunk)
        size += len(chunk)
    return {"sha256": digest.hexdigest(), "size_bytes": size}


def inspect_archive(path: Path, platform: str) -> dict:
    """Read hashes and executable identity without extraction or execution."""
    executable = "bedrock_server.exe" if platform == "windows-x64" else "bedrock_server"
    with path.open("rb") as stream:
        archive_identity = fingerprint(stream)
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            if archive.namelist().count(executable) != 1:
                raise ValueError(f"archive must contain exactly one {executable}")
            with archive.open(executable) as binary:
                executable_identity = fingerprint(binary)
            with archive.open(executable) as binary:
                header = binary.read(64)
                if platform == "linux-x64":
                    if header[:7] != b"\x7fELF\x02\x01\x01":
                        raise ValueError("expected a little-endian ELF64 executable")
                    if struct.unpack_from("<H", header, 18)[0] != 62:
                        raise ValueError("expected an x86-64 ELF executable")
                    executable_identity["format"] = "ELF64"
                    phoff = struct.unpack_from("<Q", header, 32)[0]
                    phsize, phnum = struct.unpack_from("<HH", header, 54)
                    if phsize != 56 or phnum > 4096:
                        raise ValueError("invalid ELF program headers")
                    binary.seek(phoff)
                    program_headers = binary.read(phsize * phnum)
                    for index in range(phnum):
                        kind, _, offset, _, _, size, _, _ = struct.unpack_from(
                            "<IIQQQQQQ", program_headers, index * phsize
                        )
                        if kind != 4:
                            continue
                        if size > 16 * 1024 * 1024:
                            raise ValueError("ELF note segment is too large")
                        binary.seek(offset)
                        notes = binary.read(size)
                        cursor = 0
                        while cursor + 12 <= len(notes):
                            namesz, descsz, note_type = struct.unpack_from("<III", notes, cursor)
                            cursor += 12
                            name = notes[cursor:cursor + namesz]
                            cursor += (namesz + 3) & ~3
                            value = notes[cursor:cursor + descsz]
                            cursor += (descsz + 3) & ~3
                            if cursor > len(notes):
                                raise ValueError("truncated ELF note")
                            if name == b"GNU\0" and note_type == 3:
                                executable_identity["gnu_build_id"] = value.hex()
                else:
                    if header[:2] != b"MZ":
                        raise ValueError("expected a Windows PE executable")
                    binary.seek(struct.unpack_from("<I", header, 60)[0])
                    pe = binary.read(26)
                    if pe[:6] != b"PE\0\0\x64\x86" or pe[24:26] != b"\x0b\x02":
                        raise ValueError("expected an x86-64 PE32+ executable")
                    executable_identity["format"] = "PE32+"
    return {
        "archive": {"filename": path.name, **archive_identity},
        "executable": {"filename": executable, **executable_identity},
    }


def endstone_at_least(version: str, minimum: str) -> bool:
    # Compare numeric components, never lexicographic strings (0.11.9 < 0.11.11).
    # Development builds are eligible for preparation, not native qualification.
    pattern = r"v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:(?:\.dev[0-9]+|-dev(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    actual = re.fullmatch(pattern, version)
    required = re.fullmatch(pattern, minimum)
    return bool(actual and required and
                tuple(map(int, actual.groups())) >= tuple(map(int, required.groups())))


def prepare(target: dict, archive: Path, platform: str, endstone_version: str | None) -> dict:
    if endstone_version is None:
        endstone_version = target["endstone"].get("build_version")
    if endstone_version is not None and not endstone_at_least(
        endstone_version, target["endstone"]["minimum_version"]
    ):
        raise ValueError(f"Endstone must be {target['endstone']['requirement']}; got {endstone_version!r}")
    actual = inspect_archive(archive, platform)
    expected = target["server_files"][platform]
    for section in ("archive", "executable"):
        for key, value in expected[section].items():
            # Renaming the user's ZIP does not change its binary identity.
            if key != "filename" and actual[section].get(key) != value:
                raise ValueError(f"{platform} {section} {key} mismatch")
    return {
        "schema_version": 1,
        "game_version": target.get("game_version", target["bds_package"]),
        "bds_package": target["bds_package"],
        "bds_runtime": target["bds_runtime"],
        "platform": platform,
        "endstone_requirement": target["endstone"]["requirement"],
        "selected_endstone_version": endstone_version,
        "profile_endstone_version": target["endstone"].get("build_version"),
        "profile_endstone_source_commit": target["endstone"].get("source_commit"),
        "server_files_verified": True,
        "native_adapter_qualified": (
            platform in target.get("qualified_platforms", [])
            and endstone_version.removeprefix("v") == target["endstone"].get("build_version")
        ),
        "status": target["status"],
        "remaining": target["qualification_required"],
        "server_files": actual,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--platform", choices=("linux-x64", "windows-x64"), required=True)
    parser.add_argument("--endstone-version", help="Override the profile's selected Endstone release (default: 0.11.11)")
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--output", type=Path, help="Write the preparation report as JSON")
    parser.add_argument("--require-native", action="store_true", help="Fail unless a native adapter is qualified")
    args = parser.parse_args()
    try:
        target = json.loads(args.target.read_text(encoding="utf-8"))
        report = prepare(target, args.archive, args.platform, args.endstone_version)
        result = json.dumps(report, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result, encoding="utf-8")
        print(result, end="")
        if args.require_native and not report["native_adapter_qualified"]:
            print("Native adapter qualification is pending; see remaining in the report.", file=sys.stderr)
            return 2
        return 0
    except (OSError, ValueError, KeyError, struct.error, zipfile.BadZipFile) as exc:
        print(f"BDS target preparation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
