"""Verify the built BlockData test wheel against the installed Endstone runtime."""

from __future__ import annotations

import argparse
import base64
import configparser
import copy
import csv
from email.parser import Parser
import hashlib
import importlib
import io
import json
from pathlib import Path
from pathlib import PurePosixPath
import subprocess
import sys
import sysconfig
import tempfile
from zipfile import ZipFile

from endstone.plugin import Plugin
from endstone.plugin.plugin_loader import _build_commands, _build_permissions


EXPECTED_ENTRY = "blockdata-inspector"
EXPECTED_TARGET = "endstone_blockdata_inspector:BlockDataInspectorPlugin"
EXPECTED_COMMANDS = {"bd"}
EXPECTED_DEPENDENCIES = ["blockdata_api"]
EXPECTED_PACKAGES = {"endstone_blockdata_inspector/", "endstone_blockdata/"}
EXPECTED_API_MODULES = {
    "endstone_blockdata/__init__.py",
    "endstone_blockdata/live.py",
    "endstone_blockdata/model.py",
    "endstone_blockdata/player_inventory.py",
    "endstone_blockdata/service.py",
    "endstone_blockdata/storage_item.py",
}
EXPECTED_RUNTIME_DEPENDENCIES = ["endstone==0.11.7"]
EXPECTED_VERSION = "0.5.0"
EXPECTED_BRIDGE = "_endstone_blockdata_live"
SUPPORTED_TAGS = {
    "cp314-cp314-linux_x86_64": (".so", ".cpython-314-", b"\x7fELF"),
    "cp314-cp314-win_amd64": (".pyd", ".cp314-", b"MZ"),
}


def verify_installed_runtime(wheel: Path) -> None:
    runtime_site_packages = Path(sysconfig.get_path("platlib")).resolve()
    if not (runtime_site_packages / "endstone").is_dir():
        raise AssertionError(
            f"Endstone is not installed in the wheel-test runtime: {runtime_site_packages}"
        )
    with tempfile.TemporaryDirectory(prefix="endstone-blockdata-wheel-smoke-") as temporary:
        prefix = Path(temporary) / "plugins" / ".local"
        subprocess.run(
            [
                sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                "--no-deps", "--prefix", str(prefix), str(wheel.resolve()),
            ],
            check=True,
        )
        site_packages = Path(
            sysconfig.get_path(
                "platlib", vars={"base": str(prefix), "platbase": str(prefix)}
            )
        ).resolve()
        if not site_packages.is_dir():
            raise AssertionError(f"pip did not create expected site-packages: {site_packages}")
        smoke = f"""
import copy
import importlib
from pathlib import Path
import sys
sys.path.insert(0, {json.dumps(str(runtime_site_packages))})
sys.path.insert(0, {json.dumps(str(site_packages))})
from endstone.plugin.plugin_loader import _build_commands, _build_permissions
package = importlib.import_module("endstone_blockdata_inspector")
api = importlib.import_module("endstone_blockdata")
assert hasattr(api, "ShelfView") and hasattr(api, "LiveBlockDataAdapter")
assert api.__version__ == {EXPECTED_VERSION!r}
plugin_class = package.BlockDataInspectorPlugin
assert plugin_class.api_version == "0.11"
assert set(plugin_class.commands) == {{"bd"}}
assert plugin_class.depend == ["blockdata_api"]
_build_commands(copy.deepcopy(plugin_class.commands))
_build_permissions(copy.deepcopy(plugin_class.permissions))
plugin_class()
bridge = importlib.import_module("endstone_blockdata_inspector._endstone_blockdata_live")
assert {{"available", "capabilities", "capture", "capture_region", "apply"}} <= set(dir(bridge))
assert bridge.__version__ == api.__version__
adapter = api.LiveBlockDataAdapter(None)
assert adapter.bridge is bridge
typed = {{
    "byte": bridge._NbtByte(7),
    "short": bridge._NbtShort(300),
    "int": 70000,
    "long": bridge._NbtLong(8),
    "float": bridge._NbtFloat(1.25),
    "double": 2.5,
    "Items": [{{
        "Slot": bridge._NbtByte(0),
        "Count": bridge._NbtByte(2),
        "Damage": bridge._NbtShort(0),
        "Aux": bridge._NbtShort(0),
        "LegacyId": bridge._NbtShort(1),
        "Name": "minecraft:bundle",
        "tag": {{
            "storage_item_component_content": [{{
                "Slot": bridge._NbtByte(0),
                "Count": bridge._NbtByte(3),
                "Name": "minecraft:diamond",
            }}],
        }},
    }}],
}}
roundtrip = bridge._roundtrip_nbt(copy.deepcopy(typed))
assert isinstance(roundtrip["byte"], int) and type(roundtrip["byte"]) is bridge._NbtByte
assert type(roundtrip["short"]) is bridge._NbtShort
assert type(roundtrip["int"]) is int
assert type(roundtrip["long"]) is bridge._NbtLong
assert type(roundtrip["float"]) is bridge._NbtFloat
assert type(roundtrip["double"]) is float
saved_item = roundtrip["Items"][0]
assert type(saved_item["Slot"]) is bridge._NbtByte
assert type(saved_item["Count"]) is bridge._NbtByte
assert type(saved_item["Damage"]) is bridge._NbtShort
assert type(saved_item["Aux"]) is bridge._NbtShort
assert type(saved_item["LegacyId"]) is bridge._NbtShort
nested_item = saved_item["tag"]["storage_item_component_content"][0]
assert type(nested_item["Slot"]) is bridge._NbtByte
assert type(nested_item["Count"]) is bridge._NbtByte
assert not hasattr(bridge._NbtByte(1), "__dict__")

def expect_error(error_type, callback):
    try:
        callback()
    except error_type:
        return
    raise AssertionError(f"expected {{error_type.__name__}}")

expect_error(ValueError, lambda: bridge._roundtrip_nbt(bridge._NbtByte(128)))
expect_error(ValueError, lambda: bridge._roundtrip_nbt(bridge._NbtShort(32768)))
expect_error(ValueError, lambda: bridge._roundtrip_nbt([1, "not-an-int"]))

class SpoofedByte(int):
    __endstone_nbt_scalar__ = "byte"

expect_error(TypeError, lambda: bridge._roundtrip_nbt(SpoofedByte(7)))
bridge_path = Path(bridge.__file__).resolve()
package_path = (Path({json.dumps(str(site_packages))}) / "endstone_blockdata_inspector").resolve()
assert bridge_path.is_relative_to(package_path), (bridge_path, package_path)
"""
        subprocess.run([sys.executable, "-I", "-c", smoke], check=True)


def verify(wheel: Path, *, structure_only: bool = False) -> None:
    if not wheel.is_file():
        raise SystemExit(f"wheel does not exist: {wheel}")

    with ZipFile(wheel) as archive:
        names = [item.filename for item in archive.infolist() if not item.is_dir()]
        if len(names) != len(set(names)):
            raise AssertionError("wheel contains duplicate file names")
        unsafe = [
            name for name in names
            if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
        ]
        if unsafe:
            raise AssertionError(f"wheel contains unsafe paths: {unsafe}")
        record_files = [name for name in names if name.endswith(".dist-info/RECORD")]
        if len(record_files) != 1:
            raise AssertionError(f"expected one RECORD, found {record_files}")
        rows = list(csv.reader(io.StringIO(archive.read(record_files[0]).decode("utf-8"))))
        if any(len(row) != 3 for row in rows):
            raise AssertionError("wheel RECORD contains a malformed row")
        recorded = {row[0]: (row[1], row[2]) for row in rows}
        if len(recorded) != len(rows) or set(recorded) != set(names):
            raise AssertionError("wheel RECORD file set does not match archive contents")
        for name in names:
            declared_hash, declared_size = recorded[name]
            if name == record_files[0]:
                if declared_hash or declared_size:
                    raise AssertionError("wheel RECORD must not hash itself")
                continue
            payload = archive.read(name)
            digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode()
            if declared_hash != f"sha256={digest}" or declared_size != str(len(payload)):
                raise AssertionError(f"wheel RECORD mismatch for {name}")
        entry_files = [name for name in names if name.endswith(".dist-info/entry_points.txt")]
        if len(entry_files) != 1:
            raise AssertionError(f"expected one entry_points.txt, found {entry_files}")
        parser = configparser.ConfigParser()
        parser.optionxform = str
        parser.read_string(archive.read(entry_files[0]).decode("utf-8"))
        if parser.sections() != ["endstone"]:
            raise AssertionError(f"expected only [endstone], got {parser.sections()}")
        if dict(parser["endstone"]) != {EXPECTED_ENTRY: EXPECTED_TARGET}:
            raise AssertionError(f"unexpected entry point: {dict(parser['endstone'])}")
        if any(name.endswith("endstone_plugin.toml") for name in names):
            raise AssertionError("stale endstone_plugin.toml was packaged")
        metadata_files = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_files) != 1:
            raise AssertionError(f"expected one METADATA file, found {metadata_files}")
        metadata = Parser().parsestr(archive.read(metadata_files[0]).decode("utf-8"))
        if metadata.get("Requires-Python") != "==3.14.*":
            raise AssertionError(
                f"unexpected Requires-Python: {metadata.get('Requires-Python')!r}"
            )
        if metadata.get_all("Requires-Dist", []) != EXPECTED_RUNTIME_DEPENDENCIES:
            raise AssertionError(
                f"unexpected Requires-Dist: {metadata.get_all('Requires-Dist', [])!r}"
            )
        if metadata.get("Version") != EXPECTED_VERSION:
            raise AssertionError(f"unexpected wheel version: {metadata.get('Version')!r}")
        wheel_files = [name for name in names if name.endswith(".dist-info/WHEEL")]
        if len(wheel_files) != 1:
            raise AssertionError(f"expected one WHEEL file, found {wheel_files}")
        wheel_metadata = Parser().parsestr(archive.read(wheel_files[0]).decode("utf-8"))
        if wheel_metadata.get("Root-Is-Purelib") != "false":
            raise AssertionError("command test wheel must install its native bridge in platlib")
        wheel_tags = wheel_metadata.get_all("Tag", [])
        if len(wheel_tags) != 1 or wheel_tags[0] not in SUPPORTED_TAGS:
            raise AssertionError(
                f"unexpected wheel tags: {wheel_tags!r}"
            )
        wheel_tag = wheel_tags[0]
        if not wheel.name.endswith(f"-{wheel_tag}.whl"):
            raise AssertionError(f"wheel filename does not match metadata tag {wheel_tag}")
        native_suffix, abi_marker, binary_magic = SUPPORTED_TAGS[wheel_tag]
        bridge_members = [
            name for name in names
            if PurePosixPath(name).name.startswith(f"{EXPECTED_BRIDGE}.")
            and PurePosixPath(name).suffix.lower() in {".pyd", ".so"}
        ]
        expected_parent = PurePosixPath("endstone_blockdata_inspector")
        if len(bridge_members) != 1 or PurePosixPath(bridge_members[0]).parent != expected_parent:
            raise AssertionError(
                "wheel must contain exactly one package-local BlockData live bridge; "
                f"found {bridge_members}"
            )
        bridge_name = PurePosixPath(bridge_members[0]).name
        if native_suffix != PurePosixPath(bridge_name).suffix.lower() or abi_marker not in bridge_name:
            raise AssertionError(f"native bridge ABI does not match wheel tag: {bridge_name}")
        if not archive.read(bridge_members[0]).startswith(binary_magic):
            raise AssertionError(f"native bridge has the wrong binary format: {bridge_name}")
        for package in EXPECTED_PACKAGES:
            if not any(name.startswith(package) for name in names):
                raise AssertionError(f"wheel is missing package {package}")
        missing_api_modules = EXPECTED_API_MODULES.difference(names)
        if missing_api_modules:
            raise AssertionError(
                f"wheel is missing vendored API modules: {sorted(missing_api_modules)}"
            )

    if structure_only:
        sys.path.insert(0, str(wheel.resolve()))
        module_name, class_name = EXPECTED_TARGET.split(":", 1)
        plugin_class = getattr(importlib.import_module(module_name), class_name)
        if not issubclass(plugin_class, Plugin):
            raise AssertionError(f"{EXPECTED_TARGET} is not an Endstone Plugin")
        if plugin_class.api_version != "0.11":
            raise AssertionError(f"unexpected API version: {plugin_class.api_version}")
        if set(plugin_class.commands) != EXPECTED_COMMANDS:
            raise AssertionError(f"unexpected commands: {set(plugin_class.commands)}")
        if plugin_class.depend != EXPECTED_DEPENDENCIES:
            raise AssertionError(f"unexpected native dependencies: {plugin_class.depend}")
        _build_commands(copy.deepcopy(plugin_class.commands))
        _build_permissions(copy.deepcopy(plugin_class.permissions))
        plugin_class()
    else:
        verify_installed_runtime(wheel)
    print(f"verified {wheel.name}: {EXPECTED_ENTRY}, commands={sorted(EXPECTED_COMMANDS)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--structure-only", action="store_true")
    args = parser.parse_args()
    verify(args.wheel, structure_only=args.structure_only)


if __name__ == "__main__":
    main()
