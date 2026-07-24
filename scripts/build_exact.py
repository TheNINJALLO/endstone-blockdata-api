#!/usr/bin/env python3
"""Build and package exact Endstone plugin targets with Conan dependencies."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

VERSION = "0.4.5-beta.3"
PROJECT = "blockdata"
PROJECT_SLUG = "endstone-blockdata-api"
SUPPORTED_BDS = {"1.26.32", "1.26.33"}
SUPPORTED_PLATFORMS = {"linux-x64", "windows-x64"}
BUILD_TARGETS = ['blockdata_api', '_endstone_blockdata_live']
INSTALL_COMPONENT = "blockdata_package"


def require(program: str, fallbacks: tuple[str, ...] = ()) -> str:
    resolved = shutil.which(program)
    if resolved:
        return resolved
    for candidate in fallbacks:
        if Path(candidate).is_file():
            return str(Path(candidate))
    raise SystemExit(f"Required program was not found: {program}")


def run(command: list[str], *, env: dict[str, str], log_file: Path | None = None) -> None:
    printable = subprocess.list2cmdline(command) if os.name == "nt" else " ".join(command)
    print(f"\n>>> {printable}", flush=True)
    if log_file is None:
        subprocess.run(command, check=True, env=env)
        return

    log_file.parent.mkdir(parents=True, exist_ok=True)
    tail: list[str] = []
    with log_file.open("a", encoding="utf-8", errors="replace") as handle:
        handle.write(f"\n>>> {printable}\n")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            handle.write(line)
            tail.append(line.rstrip("\n"))
            if len(tail) > 500:
                tail.pop(0)
        return_code = process.wait()

    if return_code != 0:
        print("\n========== EXACT BUILD FAILURE TAIL ==========", file=sys.stderr)
        for line in tail[-300:]:
            print(line, file=sys.stderr)
        print(f"========== FULL LOG: {log_file} ==========", file=sys.stderr)
        raise subprocess.CalledProcessError(return_code, command)


def find_toolchain(folder: Path) -> Path:
    matches = list(folder.rglob("conan_toolchain.cmake"))
    if len(matches) != 1:
        raise SystemExit(f"Expected one conan_toolchain.cmake, found {len(matches)} in {folder}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bds", required=True, choices=sorted(SUPPORTED_BDS))
    parser.add_argument("--platform", required=True, choices=sorted(SUPPORTED_PLATFORMS))
    parser.add_argument("--parallel", type=int, default=2)
    args = parser.parse_args()

    host_windows = os.name == "nt"
    if args.platform.startswith("windows") != host_windows:
        raise SystemExit(f"Platform {args.platform} does not match host OS {os.name}")
    if not 1 <= args.parallel <= 4:
        raise SystemExit("--parallel must be between 1 and 4")

    root = Path(__file__).resolve().parents[1]
    build_dir = root / "build-exact" / args.bds / args.platform
    conan_dir = build_dir / "conan"
    stage_dir = root / "dist" / "stage" / f"bds-{args.bds}-{args.platform}"
    release_dir = root / "dist" / "release"
    diagnostics_dir = root / "dist" / "diagnostics" / f"bds-{args.bds}-{args.platform}"
    log_file = diagnostics_dir / "exact-build.log"
    conan_home = root / ".conan2-ci" / args.platform

    for directory in (build_dir, stage_dir, release_dir, diagnostics_dir, conan_home):
        shutil.rmtree(directory, ignore_errors=True)

    cmake = require("cmake")
    conan = require("conan")
    ninja = require("ninja", (r"C:\ProgramData\chocolatey\bin\ninja.exe",))
    env = os.environ.copy()
    env["CMAKE_BUILD_PARALLEL_LEVEL"] = str(args.parallel)
    env["CONAN_HOME"] = str(conan_home)

    compiler_conf: str
    if host_windows:
        clang_cl = require("clang-cl", (r"C:\Program Files\LLVM\bin\clang-cl.exe",))
        lld_link = require("lld-link", (r"C:\Program Files\LLVM\bin\lld-link.exe",))
        llvm_bin = str(Path(clang_cl).parent)
        env["PATH"] = llvm_bin + os.pathsep + env.get("PATH", "")
        compiler_conf = 'tools.build:compiler_executables={"c":"clang-cl","cpp":"clang-cl"}'
    else:
        clang = require("clang-18")
        clangxx = require("clang++-18")
        env["CC"] = clang
        env["CXX"] = clangxx
        compiler_conf = 'tools.build:compiler_executables={"c":"clang-18","cpp":"clang++-18"}'

    # Endstone publishes its patched RakNet recipe on this public Conan remote.
    run([conan, "remote", "add", "endstone", "https://conan.cloudsmith.io/endstone/conan/", "--force"],
        env=env, log_file=log_file)
    run([conan, "remote", "add", "conancenter", "https://center2.conan.io", "--force"],
        env=env, log_file=log_file)
    run([conan, "profile", "detect", "--force", "--name", "exact"], env=env, log_file=log_file)

    conan_install = [
        conan, "install", str(root),
        "--output-folder", str(conan_dir),
        "--build=missing",
        "--profile:host", "exact",
        "--profile:build", "exact",
        "-s:h", "build_type=Release",
        "-s:h", "compiler.cppstd=20",
        "-s:b", "build_type=Release",
        "-c:h", "tools.cmake.cmaketoolchain:generator=Ninja",
        "-c:h", compiler_conf,
        "-c:b", "tools.cmake.cmaketoolchain:generator=Ninja",
    ]
    if not host_windows:
        conan_install += ["-s:h", "compiler=clang", "-s:h", "compiler.version=18", "-s:h", "compiler.libcxx=libc++"]
    run(conan_install, env=env, log_file=log_file)
    toolchain = find_toolchain(conan_dir)

    configure = [
        cmake,
        "-S", str(root),
        "-B", str(build_dir),
        "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=Release",
        f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
        f"-DCMAKE_MAKE_PROGRAM={ninja}",
        f"-DCMAKE_INSTALL_PREFIX={stage_dir}",
        "-DENDSTONE_BLOCKDATA_BUILD_TESTS=OFF",
        "-DENDSTONE_BLOCKDATA_BUILD_PLUGIN=ON",
        "-DENDSTONE_BLOCKDATA_BUILD_NATIVE_2630=OFF",
        f"-DENDSTONE_BDS_BUILD={args.bds}",
    ]
    configure.append("-DENDSTONE_BLOCKDATA_BUILD_LIVE_PYTHON=ON")

    if host_windows:
        configure += [
            f"-DCMAKE_C_COMPILER={clang_cl}",
            f"-DCMAKE_CXX_COMPILER={clang_cl}",
            f"-DCMAKE_LINKER={lld_link}",
        ]
    else:
        configure += [
            f"-DCMAKE_C_COMPILER={clang}",
            f"-DCMAKE_CXX_COMPILER={clangxx}",
        ]

    print(f"Building {PROJECT_SLUG} {VERSION} for BDS {args.bds} ({args.platform})")
    print(f"Targets: {', '.join(BUILD_TARGETS)}; parallel jobs: {args.parallel}")
    run([cmake, "--version"], env=env)
    run([conan, "--version"], env=env)
    run(configure, env=env, log_file=log_file)

    for target in BUILD_TARGETS:
        run([
            cmake, "--build", str(build_dir),
            "--config", "Release",
            "--target", target,
            "--parallel", str(args.parallel),
            "--verbose",
        ], env=env, log_file=log_file)

    run([
        cmake, "--install", str(build_dir),
        "--config", "Release",
        "--component", INSTALL_COMPONENT,
    ], env=env, log_file=log_file)

    run([
        sys.executable,
        str(root / "scripts" / "package_release.py"),
        "--project", PROJECT,
        "--version", VERSION,
        "--bds", args.bds,
        "--platform", args.platform,
        "--stage", str(stage_dir),
        "--release-dir", str(release_dir),
    ], env=env, log_file=log_file)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        print(f"Exact build failed with exit code {error.returncode}.", file=sys.stderr)
        raise SystemExit(error.returncode) from None
