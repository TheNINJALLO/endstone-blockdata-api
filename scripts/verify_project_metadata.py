#!/usr/bin/env python3
"""Fail when release/API versions drift across project metadata."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = {
    "endstone-blockdata-api": {
        "bridge_module": "_endstone_blockdata_live",
        "wheel_package": "endstone_blockdata_inspector",
        "package_init": "python/endstone_blockdata/__init__.py",
        "wheel_pyproject": "examples/python/block_data_inspector_plugin/pyproject.toml",
        "wheel_plugin": (
            "examples/python/block_data_inspector_plugin/src/"
            "endstone_blockdata_inspector/plugin.py"
        ),
        "version_macro": "ENDSTONE_BLOCKDATA_VERSION",
    },
    "endstone-worldgen-api": {
        "bridge_module": "_endstone_worldgen_live",
        "wheel_package": "endstone_worldgen_studio",
        "package_init": "python/endstone_worldgen/__init__.py",
        "wheel_pyproject": "examples/python/world_gen_studio_plugin/pyproject.toml",
        "wheel_plugin": (
            "examples/python/world_gen_studio_plugin/src/"
            "endstone_worldgen_studio/plugin.py"
        ),
        "version_macro": "ENDSTONE_WORLDGEN_VERSION",
    },
}


def capture(path: str, pattern: str, label: str) -> str:
    text = (ROOT / path).read_text(encoding="utf-8")
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        raise SystemExit(f"Could not find {label} in {path}")
    return match.group(1)


def pep440_version(release: str) -> tuple[str, str]:
    match = re.fullmatch(r"(\d+\.\d+\.\d+)(?:-(alpha|beta|rc)\.(\d+))?", release)
    if not match:
        raise SystemExit(f"Unsupported SOURCE_RELEASE.json version: {release!r}")
    base, phase, serial = match.groups()
    if phase is None:
        return base, base
    marker = {"alpha": "a", "beta": "b", "rc": "rc"}[phase]
    return base, f"{base}{marker}{serial}"


def main() -> int:
    source = json.loads((ROOT / "SOURCE_RELEASE.json").read_text(encoding="utf-8"))
    slug = source.get("name")
    if slug not in CONFIGS:
        raise SystemExit(f"Unknown project in SOURCE_RELEASE.json: {slug!r}")
    config = CONFIGS[slug]
    release = source.get("version")
    if not isinstance(release, str):
        raise SystemExit("SOURCE_RELEASE.json version must be a string")
    base, python_version = pep440_version(release)

    compatibility = json.loads(
        (ROOT / "compatibility/versions.json").read_text(encoding="utf-8")
    )
    checks = {
        "CMake project version": (
            capture("CMakeLists.txt", r"project\([^\n]*\bVERSION\s+([^\s\)]+)", "project version"),
            base,
        ),
        "Python package version": (
            capture(config["package_init"], r'^__version__\s*=\s*"([^"]+)"', "__version__"),
            python_version,
        ),
        "root wheel version": (
            capture("pyproject.toml", r'^version\s*=\s*"([^"]+)"', "project version"),
            python_version,
        ),
        "test wheel version": (
            capture(config["wheel_pyproject"], r'^version\s*=\s*"([^"]+)"', "test wheel version"),
            python_version,
        ),
        "test wheel Python version": (
            capture(config["wheel_pyproject"], r'^requires-python\s*=\s*"([^"]+)"', "requires-python"),
            "==3.14.*",
        ),
        "test wheel Endstone dependency": (
            capture(
                config["wheel_pyproject"],
                r'^dependencies\s*=\s*\[\s*"([^"]+)"\s*,?\s*\]',
                "test wheel dependency",
            ),
            "endstone==0.11.6",
        ),
        "test plugin version": (
            capture(config["wheel_plugin"], r'^\s+version\s*=\s*"([^"]+)"', "plugin version"),
            release,
        ),
        "test plugin Endstone API": (
            capture(config["wheel_plugin"], r'^\s+api_version\s*=\s*"([^"]+)"', "api_version"),
            "0.11",
        ),
        "workflow release version": (
            capture(".github/workflows/ci.yml", r"^\s*RELEASE_VERSION:\s*([^\s]+)", "RELEASE_VERSION"),
            release,
        ),
        "compatibility API version": (compatibility.get("api"), base),
        "build status version": (
            capture("BUILD_STATUS.md", r"^Version:\s*\*\*([^*]+)\*\*", "build status version"),
            release,
        ),
        "installation guide tag": (
            capture("docs/INSTALL.md", r"`v([^`]+)`", "installation release tag"),
            release,
        ),
        "release guide tag": (
            capture("docs/GITHUB_RELEASES.md", r"git tag v([^\s]+)", "release guide tag"),
            release,
        ),
        "version header source": (
            capture(
                "include/version.h.in",
                rf'#define\s+{config["version_macro"]}\s+"([^"]+)"',
                "version macro",
            ),
            f"@{config['version_macro'].removesuffix('_VERSION')}_RELEASE_VERSION@",
        ),
    }
    failures = [
        f"{label}: expected {expected!r}, got {actual!r}"
        for label, (actual, expected) in checks.items()
        if actual != expected
    ]
    workflow_text = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    workflow_python_versions = re.findall(
        r'^\s*python-version:\s*"([^"]+)"', workflow_text, re.MULTILINE
    )
    if workflow_python_versions != ["3.14"] * 5:
        failures.append(
            "All metadata, portable, exact, test-wheel, and release jobs must use Python 3.14; "
            f"got {workflow_python_versions!r}"
        )
    supported_bds = source.get("supported_bds", [])
    endstone_tags = source.get("endstone_tags", [])
    if slug == "endstone-blockdata-api":
        if supported_bds != ["1.26.33"]:
            failures.append(
                f"BlockData exact BDS support must be ['1.26.33'], got {supported_bds!r}"
            )
        if endstone_tags != ["v0.11.6"]:
            failures.append(
                f"BlockData exact Endstone support must be ['v0.11.6'], got {endstone_tags!r}"
            )
        workflow_bds = source.get("github_actions", {}).get("bds")
        if workflow_bds != supported_bds:
            failures.append(
                f"GitHub Actions BDS matrix metadata must equal supported_bds, got {workflow_bds!r}"
            )
    if len(supported_bds) != len(endstone_tags):
        failures.append("supported_bds and endstone_tags must have a one-to-one mapping")
    expected_tag_map = dict(zip(supported_bds, endstone_tags))
    cmake_text = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    configured_tag_map = dict(
        re.findall(
            r'(?:if|elseif)\(ENDSTONE_BDS_BUILD STREQUAL "([^"]+)"\)\s*'
            r'set\(ENDSTONE_EXACT_TAG "([^"]+)"\)',
            cmake_text,
        )
    )
    if configured_tag_map != expected_tag_map:
        failures.append(
            f"CMake exact BDS/tag mapping: expected {expected_tag_map!r}, "
            f"got {configured_tag_map!r}"
        )
    compatibility_map = {
        adapter.get("bds"): f"v{adapter.get('endstone')}"
        for adapter in compatibility.get("adapters", [])
        if isinstance(adapter, dict)
    }
    if compatibility_map != expected_tag_map:
        failures.append(
            f"compatibility adapter mapping: expected {expected_tag_map!r}, "
            f"got {compatibility_map!r}"
        )
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if f"v{release}" not in readme:
        failures.append(f"README.md does not reference release tag v{release}")
    wheel_project = Path(config["wheel_pyproject"])
    wheel_project_text = (ROOT / wheel_project).read_text(encoding="utf-8")
    for required in (
        "setuptools>=80",
        "wheel>=0.45",
        f'{config["bridge_module"]}*.pyd',
        f'{config["bridge_module"]}*.so',
    ):
        if required not in wheel_project_text:
            failures.append(f"Test wheel packaging is missing {required!r}")
    setup_text = (ROOT / wheel_project.parent / "setup.py").read_text(encoding="utf-8")
    if "has_ext_modules" not in setup_text or "return True" not in setup_text:
        failures.append("Test wheel setup.py must force a platform-specific binary wheel tag")
    build_exact_text = (ROOT / "scripts/build_exact.py").read_text(encoding="utf-8")
    if "build_test_wheel.py" not in build_exact_text or '"--stage-dir"' not in build_exact_text:
        failures.append("Exact build must create and bundle its matching platform command wheel")
    for required in (
        "cp314-cp314-linux_x86_64",
        "cp314-cp314-win_amd64",
        "--structure-only",
        "Smoke-test relocated Linux command wheel",
        "Smoke-test relocated Windows command wheel",
        "Verify complete release asset set",
        "verify_combined_release_assets.py",
        "create_flags=(--latest)",
        "create_flags=(--prerelease --latest=false)",
        "wc -l < SHA256SUMS.txt",
    ):
        if required not in workflow_text:
            failures.append(f"Workflow platform-wheel contract is missing {required!r}")
    if failures:
        raise SystemExit("Metadata verification failed:\n- " + "\n- ".join(failures))

    print(f"Verified metadata for {slug} {release}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
