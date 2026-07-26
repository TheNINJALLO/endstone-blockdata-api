#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

BRIDGE_MODULES = {
    "endstone-blockdata-api": "_endstone_blockdata_live",
    "endstone-worldgen-api": "_endstone_worldgen_live",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_archive_path(path: str) -> bool:
    candidate = PurePosixPath(path)
    return bool(candidate.parts) and not candidate.is_absolute() and ".." not in candidate.parts


def verify_checksum_file(checksums: Path, expected: dict[str, str]) -> None:
    declared: dict[str, str] = {}
    for line in checksums.read_text(encoding="utf-8").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise SystemExit(f"Malformed checksum line in {checksums}: {line!r}")
        digest, name = parts
        declared[name.lstrip("*")] = digest.lower()
    if declared != expected:
        raise SystemExit(
            f"Checksum manifest mismatch in {checksums}: expected {expected}, got {declared}"
        )


def verify_linux_dynamic_symbols(plugin: Path) -> None:
    nm = shutil.which("nm")
    if not nm:
        raise SystemExit("GNU nm is required to validate Linux release symbols")
    result = subprocess.run(
        [nm, "-D", "--undefined-only", str(plugin)],
        check=True,
        capture_output=True,
        text=True,
    )
    bedrock_symbol = re.compile(
        r"^_Z(?:NK?|TV|TI|TS)(?:[0-9]+(?:BaseGameVersion|Block|BlockActor|"
        r"BlockSource|BlockType|ByteArrayTag|ByteTag|CompoundTag|Container|"
        r"Dimension|DoubleTag|EndTag|FloatTag|HashedString|Int64Tag|IntArrayTag|"
        r"IntTag|Item|ItemDescriptor|ItemInstance|ItemRegistry|ItemRegistryManager|"
        r"ItemStack|ItemStackBase|IVanillaMainBlockActorComponent|LevelChunk|"
        r"ListTag|ShortTag|StringTag|Tag|WeakPtr|WeakRef)|"
        r"8endstone4core17EndstoneDimension)"
    )
    unresolved_bedrock = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[-2] == "U" and bedrock_symbol.match(fields[-1]):
            unresolved_bedrock.append(fields[-1])
    if unresolved_bedrock:
        rendered = "\n  ".join(sorted(set(unresolved_bedrock)))
        raise SystemExit(
            "Linux plugin contains strong unresolved Bedrock ABI symbols that can make dlopen fail:\n"
            f"  {rendered}"
        )

    readelf = shutil.which("readelf")
    if not readelf:
        raise SystemExit("GNU readelf is required to validate Linux release RPATH")
    dynamic = subprocess.run(
        [readelf, "--dynamic", str(plugin)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    nonportable_runtime = re.compile(
        r"^(?:libstdc\+\+|libc\+\+|libc\+\+abi|libgcc_s)\.so(?:\.|$)"
    )
    for line in dynamic.splitlines():
        if "(NEEDED)" in line:
            match = re.search(r"\[([^]]+)\]", line)
            needed = "" if match is None else match.group(1)
            if nonportable_runtime.match(needed):
                raise SystemExit(
                    f"Linux binary depends on non-bundled C++ runtime {needed}: {plugin}"
                )
        if "(RPATH)" not in line and "(RUNPATH)" not in line:
            continue
        match = re.search(r"\[([^]]*)\]", line)
        entries = [] if match is None else match.group(1).split(":")
        unsafe = [
            entry for entry in entries
            if entry and entry != "$ORIGIN" and not entry.startswith("$ORIGIN/")
        ]
        if unsafe:
            raise SystemExit(f"Linux plugin contains non-relocatable RPATH entries: {unsafe}")


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

    expected_magic = b"MZ" if args.platform.startswith("windows") else b"\x7fELF"
    with raw.open("rb") as handle:
        if handle.read(len(expected_magic)) != expected_magic:
            raise SystemExit(f"Unexpected binary format for {raw}")

    verify_checksum_file(
        checksums,
        {
            raw.name: sha256_file(raw),
            archive.name: sha256_file(archive),
        },
    )

    with ZipFile(archive) as zf:
        bad = zf.testzip()
        if bad:
            raise SystemExit(f"Corrupt ZIP member: {bad}")
        members = [info.filename for info in zf.infolist() if not info.is_dir()]
        if len(members) != len(set(members)):
            raise SystemExit("Release archive contains duplicate file names")
        unsafe = [name for name in members if not safe_archive_path(name)]
        if unsafe:
            raise SystemExit(f"Release archive contains unsafe paths: {unsafe}")
        manifests = [name for name in members if name.endswith("/PACKAGE_MANIFEST.json")]
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

    if manifest.get("schema") != 1:
        raise SystemExit(f"Unsupported package manifest schema: {manifest.get('schema')}")

    archive_root = f"{stem}/"
    if manifests[0] != f"{archive_root}PACKAGE_MANIFEST.json":
        raise SystemExit(f"Unexpected archive root: {manifests[0]}")

    declared_files = manifest.get("files")
    if not isinstance(declared_files, list):
        raise SystemExit("PACKAGE_MANIFEST.json files must be a list")
    declared_members: set[str] = set()
    with ZipFile(archive) as zf:
        for entry in declared_files:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                raise SystemExit(f"Malformed package manifest file entry: {entry!r}")
            relative = entry["path"]
            if not safe_archive_path(relative):
                raise SystemExit(f"Unsafe path in package manifest: {relative}")
            member = f"{archive_root}{relative}"
            if member in declared_members:
                raise SystemExit(f"Duplicate path in package manifest: {relative}")
            declared_members.add(member)
            try:
                payload = zf.read(member)
            except KeyError as exc:
                raise SystemExit(f"Manifest file is missing from archive: {relative}") from exc
            if entry.get("size") != len(payload):
                raise SystemExit(f"Manifest size mismatch for {relative}")
            if entry.get("sha256") != sha256_bytes(payload):
                raise SystemExit(f"Manifest SHA-256 mismatch for {relative}")

        actual_payload = set(members) - {manifests[0]}
        if actual_payload != declared_members:
            missing = sorted(declared_members - actual_payload)
            extra = sorted(actual_payload - declared_members)
            raise SystemExit(f"Archive/manifest file-set mismatch; missing={missing}, extra={extra}")

        primary = manifest.get("primary_plugin")
        if not isinstance(primary, str) or f"{archive_root}{primary}" not in declared_members:
            raise SystemExit(f"Invalid primary_plugin in package manifest: {primary!r}")
        if sha256_bytes(zf.read(f"{archive_root}{primary}")) != sha256_file(raw):
            raise SystemExit("Raw plugin does not match the primary plugin stored in the archive")

        supported_native_suffixes = {".dll", ".pyd"} if args.platform.startswith("windows") else {".so"}
        native_members = [
            name for name in members
            if PurePosixPath(name).suffix.lower() in {".dll", ".pyd", ".so", ".dylib"}
        ]
        unexpected_native = [
            name for name in native_members
            if PurePosixPath(name).suffix.lower() not in supported_native_suffixes
        ]
        if unexpected_native:
            raise SystemExit(
                f"Release archive contains native binaries for the wrong platform: {unexpected_native}"
            )
        if not native_members:
            raise SystemExit("Release archive does not contain a native plugin or bridge")

        bridge_base = BRIDGE_MODULES.get(args.slug)
        if bridge_base is None:
            raise SystemExit(f"No native Python bridge is defined for project {args.slug!r}")
        python_dir = PurePosixPath(archive_root) / "python"
        bridge_members = [
            name for name in native_members
            if PurePosixPath(name).parent == python_dir
            and PurePosixPath(name).name.startswith(f"{bridge_base}.")
            and PurePosixPath(name).suffix.lower() in supported_native_suffixes
        ]
        if len(bridge_members) != 1:
            raise SystemExit(
                f"Expected exactly one {bridge_base} native bridge in archive python/, "
                f"found {bridge_members}"
            )
        bridge_filename = PurePosixPath(bridge_members[0]).name
        expected_abi_marker = (
            ".cp312-" if args.platform.startswith("windows") else ".cpython-312-"
        )
        if expected_abi_marker not in bridge_filename:
            raise SystemExit(
                f"Native Python bridge must use the CPython 3.12 SOABI filename marker "
                f"{expected_abi_marker!r}, got {bridge_filename!r}"
            )

        archive_magic = b"MZ" if args.platform.startswith("windows") else b"\x7fELF"
        with tempfile.TemporaryDirectory(prefix="endstone-release-verify-") as temp_dir:
            for index, member in enumerate(native_members):
                payload = zf.read(member)
                if not payload.startswith(archive_magic):
                    raise SystemExit(f"Unexpected binary format for archive member {member}")
                if args.platform.startswith("linux"):
                    extracted = Path(temp_dir) / f"{index}-{PurePosixPath(member).name}"
                    extracted.write_bytes(payload)
                    verify_linux_dynamic_symbols(extracted)

    # The archive loop verifies the primary plugin and every bundled native
    # Python bridge. Checking only the raw plugin can miss an import-time
    # undefined symbol or build-runner RPATH in the command wheel's bridge.

    print(f"Verified {raw.name}")
    print(f"Verified {archive.name}")
    print(f"Verified {checksums.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
