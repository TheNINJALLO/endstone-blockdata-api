#!/usr/bin/env python3
"""Package only committed source and the portable API for a compatibility alpha."""
from __future__ import annotations

import argparse
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def validate_release(source: dict) -> None:
    match = re.fullmatch(r"(\d+\.\d+\.\d+)-alpha\.(\d+)", source["version"])
    if (not match or source.get("release_channel") != "compatibility-prerelease"
            or source.get("native_release_ready") is not False):
        raise ValueError("Only an explicitly unqualified compatibility alpha may use this packager")
    if source.get("python_version") != f"{match[1]}a{match[2]}":
        raise ValueError("Python and release versions differ")


def verify_wheel(path: Path, source: dict) -> None:
    with ZipFile(path) as archive:
        names = archive.namelist()
        if any(name.lower().endswith((".dll", ".so", ".pyd", ".dylib")) for name in names):
            raise ValueError("Compatibility releases must not contain native binaries")
        metadata = BytesParser().parsebytes(archive.read(next(
            name for name in names if name.endswith(".dist-info/METADATA"))))
        wheel = BytesParser().parsebytes(archive.read(next(
            name for name in names if name.endswith(".dist-info/WHEEL"))))
        if metadata["Version"] != source["python_version"] or metadata["Name"] != source["name"]:
            raise ValueError("Wheel metadata does not match the release")
        if wheel["Root-Is-Purelib"] != "true" or wheel.get_all("Tag") != ["py3-none-any"]:
            raise ValueError("Expected a pure Python, platform independent API wheel")
        if any(name.endswith(".dist-info/entry_points.txt") and
               "[endstone]" in archive.read(name).decode("utf-8") for name in names):
            raise ValueError("An Endstone command plugin cannot be released as a portable API")


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-tag", action="store_true")
    args = parser.parse_args()
    source = json.loads((ROOT / "SOURCE_RELEASE.json").read_text(encoding="utf-8"))
    validate_release(source)
    if git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("Commit tracked changes before packaging a release")
    commit = git("rev-parse", "HEAD")
    tag = "v" + source["version"]
    if args.require_tag and git("rev-parse", tag + "^{commit}") != commit:
        raise SystemExit("Release tag does not identify HEAD")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise SystemExit("Output directory must be empty to prevent stale release assets")
    stem = source["name"] + "-" + tag
    source_zip = output / (stem + "-source.zip")
    subprocess.run(["git", "-C", str(ROOT), "archive", "--format=zip",
                    "--prefix=" + stem + "/", "--output=" + str(source_zip), commit], check=True)
    with tempfile.TemporaryDirectory(prefix="compatibility-release-") as temporary:
        with ZipFile(source_zip) as archive:
            archive.extractall(temporary)
        clean_source = Path(temporary) / stem
        subprocess.run([sys.executable, "-m", "build", "--wheel", "--no-isolation",
                        "--outdir", str(output), str(clean_source)], check=True)
    wheels = list(output.glob("*.whl"))
    if len(wheels) != 1:
        raise SystemExit("Expected exactly one portable API wheel")
    verify_wheel(wheels[0], source)
    shutil.copyfile(ROOT / "compatibility/bds-1.26.51.json", output / "bds-1.26.51.json")
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(output.iterdir())}
    manifest = {"project": source["name"], "version": source["version"],
                "python_version": source["python_version"], "git_commit": commit,
                "tag": tag, "release_channel": source["release_channel"],
                "native_release_ready": False, "game_version": "1.26.51",
                "endstone_requirement": source["endstone_requirement"],
                "assets_sha256": hashes}
    (output / "COMPATIBILITY_RELEASE.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    checksums = "".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
                        for path in sorted(output.iterdir()))
    (output / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8")
    print(f"Verified source and portable API release {tag} from {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
