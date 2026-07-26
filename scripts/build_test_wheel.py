#!/usr/bin/env python3
"""Build the command-test wheel with its exact native bridge bundled inside."""
from __future__ import annotations

import argparse
from email.parser import Parser
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
WHEEL_PROJECT = Path("examples/python/block_data_inspector_plugin")
WHEEL_PACKAGE = Path("src/endstone_blockdata_inspector")
PACKAGE_NAME = "endstone_blockdata_inspector"
BRIDGE_MODULE = "_endstone_blockdata_live"
REQUIRED_PYTHON = (3, 14)


def platform_tag() -> str:
    return sysconfig.get_platform().replace("-", "_").replace(".", "_")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a platform-specific Endstone command wheel around an exact bridge."
    )
    parser.add_argument("--bridge", type=Path, required=True)
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist" / "release")
    args = parser.parse_args()

    if sys.implementation.name != "cpython" or sys.version_info[:2] != REQUIRED_PYTHON:
        raise SystemExit(
            "Command wheels with a native bridge must be built with CPython 3.14; "
            f"running {sys.implementation.name} {sys.version_info.major}.{sys.version_info.minor}"
        )

    stage_dir = args.stage_dir.resolve()
    if not stage_dir.is_dir():
        raise SystemExit(f"Exact install stage does not exist: {stage_dir}")
    if args.bridge.is_symlink():
        raise SystemExit(f"Native bridge must not be a symbolic link: {args.bridge}")
    bridge = args.bridge.resolve()
    try:
        bridge.relative_to(stage_dir / "python")
    except ValueError as exc:
        raise SystemExit(
            f"Native bridge must be inside the exact stage's python directory: {bridge}"
        ) from exc
    if not bridge.is_file() or bridge.stat().st_size == 0:
        raise SystemExit(f"Native bridge is missing or empty: {bridge}")
    extension_suffix = sysconfig.get_config_var("EXT_SUFFIX")
    if not isinstance(extension_suffix, str) or not extension_suffix:
        raise SystemExit("CPython did not report an EXT_SUFFIX for native modules")
    expected_bridge_name = BRIDGE_MODULE + extension_suffix
    if bridge.name != expected_bridge_name:
        raise SystemExit(
            f"Native bridge must use this CPython's extension suffix; got {bridge.name!r}, "
            f"expected {expected_bridge_name!r}"
        )
    expected_magic = b"MZ" if sys.platform == "win32" else b"\x7fELF"
    if bridge.read_bytes()[: len(expected_magic)] != expected_magic:
        raise SystemExit(f"Native bridge has the wrong binary format for this host: {bridge}")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns(
        ".git", ".conan2-ci", "build", "build-*", "dist", "__pycache__",
        "*.egg-info", "*.dll", "*.pyd", "*.so",
    )
    with tempfile.TemporaryDirectory(prefix="endstone-blockdata-wheel-") as temporary:
        staged_root = Path(temporary) / "repo"
        shutil.copytree(ROOT, staged_root, ignore=ignore)
        staged_project = staged_root / WHEEL_PROJECT
        staged_package = staged_project / WHEEL_PACKAGE
        staged_package.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bridge, staged_package / bridge.name)

        build_output = Path(temporary) / "wheel"
        subprocess.run(
            [
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--no-isolation",
                "--outdir",
                str(build_output),
                str(staged_project),
            ],
            check=True,
        )
        wheels = list(build_output.glob("*.whl"))
        if len(wheels) != 1:
            raise SystemExit(f"Expected one command wheel, found {len(wheels)}: {wheels}")
        wheel = wheels[0]
        expected_tag = f"cp314-cp314-{platform_tag()}"
        if not wheel.name.endswith(f"-{expected_tag}.whl"):
            raise SystemExit(
                f"Command wheel has the wrong compatibility tag: {wheel.name}; "
                f"expected {expected_tag}"
            )

        with ZipFile(wheel) as archive:
            names = archive.namelist()
            expected_bridge = f"{PACKAGE_NAME}/{bridge.name}"
            if names.count(expected_bridge) != 1:
                raise SystemExit(
                    f"Command wheel must contain exactly one package-local bridge {expected_bridge}"
                )
            wheel_metadata_files = [name for name in names if name.endswith(".dist-info/WHEEL")]
            if len(wheel_metadata_files) != 1:
                raise SystemExit("Command wheel must contain exactly one WHEEL metadata file")
            metadata = Parser().parsestr(
                archive.read(wheel_metadata_files[0]).decode("utf-8")
            )
            if metadata.get("Root-Is-Purelib") != "false":
                raise SystemExit("Command wheel containing a native bridge must not be pure Python")
            if metadata.get_all("Tag", []) != [expected_tag]:
                raise SystemExit(
                    f"Command wheel metadata tag mismatch: {metadata.get_all('Tag', [])!r}"
                )

        destination = output_dir / wheel.name
        shutil.copy2(wheel, destination)
        bundled_destination = stage_dir / "plugins" / wheel.name
        bundled_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wheel, bundled_destination)

    print(destination)
    print(bundled_destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
