"""Verify the built BlockData test wheel against the installed Endstone runtime."""

from __future__ import annotations

import argparse
import configparser
import copy
from email.parser import Parser
import importlib
from pathlib import Path
import sys
from zipfile import ZipFile

from endstone.plugin import Plugin
from endstone.plugin.plugin_loader import _build_commands, _build_permissions


EXPECTED_ENTRY = "blockdata-inspector"
EXPECTED_TARGET = "endstone_blockdata_inspector:BlockDataInspectorPlugin"
EXPECTED_COMMANDS = {"bd"}
EXPECTED_DEPENDENCIES = ["blockdata_api"]
EXPECTED_PACKAGES = {"endstone_blockdata_inspector/"}


def verify(wheel: Path) -> None:
    if not wheel.is_file():
        raise SystemExit(f"wheel does not exist: {wheel}")

    with ZipFile(wheel) as archive:
        names = archive.namelist()
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
        if metadata.get("Requires-Python") != "==3.12.*":
            raise AssertionError(
                f"unexpected Requires-Python: {metadata.get('Requires-Python')!r}"
            )
        for package in EXPECTED_PACKAGES:
            if not any(name.startswith(package) for name in names):
                raise AssertionError(f"wheel is missing package {package}")

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
    print(f"verified {wheel.name}: {EXPECTED_ENTRY}, commands={sorted(EXPECTED_COMMANDS)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    verify(args.wheel)


if __name__ == "__main__":
    main()
