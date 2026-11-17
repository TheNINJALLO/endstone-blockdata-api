"""Promote successful CI artifacts from an unchanged commit merged into main."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kwargs).stdout.strip()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def one(folder, name):
    paths = [p for p in folder.rglob(name) if p.is_file()]
    require(len(paths) == 1, f"Expected one {name}, found {len(paths)}")
    return paths[0]


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def checksums(folder, filename):
    for line in (folder / filename).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        name = name.lstrip("* ")
        require(Path(name).name == name, f"Invalid checksum path: {name}")
        require((folder / name).is_file() and sha(folder / name) == digest, f"Checksum mismatch: {name}")


def verify_enchantment(proof, source):
    require(proof.get("production_ready") is True, "Enchantment production gate is closed")
    require(proof.get("git_commit") == source, "Qualification commit differs from the release tag")
    require(proof.get("version") == "1.1.8", "Wrong Enchantment version")
    require(proof.get("targets", {}).get("endstone_tag") == "v0.11.16", "Wrong Endstone target")
    require(proof.get("targets", {}).get("bds_package") == "1.26.65.1", "Wrong BDS target")
    live = proof.get("results", {}).get("live_server", {})
    require(live.get("passed") and live.get("clean_shutdown") and live.get("owned_projectile_probe_verified"), "Missing live qualification")


def verify_blockdata(proof, wheel):
    require(proof.get("passed") and proof.get("persisted_restart") and proof.get("clean_shutdown"), "Missing BlockData restart qualification")
    require(proof.get("endstone") == "0.11.16" and proof.get("bds") == "1.26.65.1", "Wrong BlockData target")
    require(proof.get("wheel_sha256") == sha(wheel), "Live-tested BlockData wheel differs")
    require([p.get("mode") for p in proof.get("phases", [])] == ["write", "verify"], "Both restart phases are required")
    require(all(p.get("passed") is True and all(p.get("checks", {}).values()) for p in proof["phases"]), "A BlockData phase failed")


def verify_worldchunks(proof, files, platform):
    require(proof.get("passed") is True and proof.get("platform") == platform, "Wrong WorldChunks qualification")
    require(proof.get("endstone") == "0.11.16" and proof.get("bds") == "1.26.65.1" and proof.get("enable_script") is True, "Wrong WorldChunks runtime")
    expected = {"exact native hooks installed", "headless fixture has no players", "cleanup evicts unprotected ticking-area chunk", "cleanup preserves manual pin", "disabling cleanup restores vanilla residency", "saved block survives native eviction and reload", "native plugins shut down cleanly", "matching bundle wheel loads both plugins", "chunk policy survives restart", "saved block survives full server restart", "bundle plugins shut down cleanly"}
    checks = {c["test"]: c["passed"] for c in proof.get("checks", [])}
    require(set(checks) == expected and all(v is True for v in checks.values()), "Incomplete WorldChunks runtime checks")
    require(set(proof.get("artifacts", {})) == {p.name for p in files}, "Wrong WorldChunks artifact set")
    for path in files:
        require(proof["artifacts"][path.name] == sha(path), f"Qualified binary differs: {path.name}")


def prepare(config, incoming, source, stage):
    require(not stage.exists(), "Release staging directory already exists")
    stage.mkdir(parents=True)
    kind, version = config["kind"], config["version"]
    require(config["tag"] == "v" + version, "Tag/version mismatch")
    cmake = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    require(re.search(r"project\([^\n]*\bVERSION\s+" + re.escape(version) + r"(?:\s|\))", cmake), "CMake release version differs")
    if kind != "worldchunks":
        require(read(ROOT / "SOURCE_RELEASE.json")["version"] == version, "Source release version differs")
    if kind == "enchantment":
        folder = one(incoming, "PRODUCTION_QUALIFICATION.json").parent
        verify_enchantment(read(folder / "PRODUCTION_QUALIFICATION.json"), source)
        checksums(folder, "SHA256SUMS.txt")
        names = ["endstone_enchantment_plugin.so", f"endstone_enchantment_api-{version}-py3-none-any.whl", f"endstone_enchantment_partner-{version}-cp314-cp314-linux_x86_64.whl", f"endstone-enchantment-api-v{version}-linux-x64-deployment.zip", f"endstone-enchantment-api-v{version}-sdk-linux-x64.tar.gz", "ENCHANTMENTS.md", "ARMOR_SETS.md", "PRODUCTION_QUALIFICATION.json", f"endstone-enchantment-api-v{version}.cdx.json"]
        for name in names:
            copy(folder / name, stage / name)
    elif kind == "blockdata":
        wheel = one(incoming, f"endstone_blockdata_inspector-{version}-cp314-cp314-linux_x86_64.whl")
        proof = read(one(incoming, "probe.json"))
        verify_blockdata(proof, wheel)
        folder = wheel.parent
        stem = f"endstone-blockdata-api-v{version}-bds-1.26.65-linux-x64"
        checksums(folder, stem + ".sha256")
        for name in [stem + ".so", stem + ".zip", stem + ".sha256", wheel.name]:
            copy(folder / name, stage / name)
        result = subprocess.run([sys.executable, str(ROOT / "scripts/verify_combined_release_assets.py"), "--slug", "endstone-blockdata-api", "--version", version, "--bds", "1.26.65", "--release-dir", str(stage), "--platform", "linux-x64"], text=True, capture_output=True)
        require(result.returncode == 0, result.stdout + result.stderr)
        proof.update(source_commit=source)
        (stage / "QUALIFICATION.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    elif kind == "worldchunks":
        for platform, tag, build, extension in [("linux", "linux_x86_64", "build", ".so"), ("windows", "win_amd64", "build-windows", ".dll")]:
            wheel = one(incoming, f"endstone_worldchunks_bundle-{version}-py3-none-{tag}.whl")
            binaries = [one(incoming, "endstone_" + n + extension) for n in ("worldchunks", "worldchunks_optimizer")]
            suffix = f"evidence/endstone-0.11.16/{tag}/qualification.json"
            reports = [p for p in incoming.rglob("qualification.json") if p.as_posix().endswith(suffix)]
            require(len(reports) == 1, f"Missing current {platform} runtime report")
            proof = read(reports[0])
            verify_worldchunks(proof, [*binaries, wheel], platform)
            for binary in binaries:
                copy(binary, ROOT / build / binary.name)
            copy(wheel, ROOT / "dist" / wheel.name)
            proof.update(source_commit=source)
            target = ROOT / "evidence/endstone-0.11.16" / ("linux-x64" if platform == "linux" else "windows-x64") / "qualification.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
        run(sys.executable, str(ROOT / "scripts/package.py"))
        run(sys.executable, str(ROOT / "scripts/check_release.py"))
        names = [line.split("  ", 1)[1] for line in (ROOT / "dist/SHA256SUMS").read_text().splitlines()]
        for name in names:
            copy(ROOT / "dist" / name, stage / name)
    else:
        raise ValueError("Unknown release kind")
    paths = sorted(p for p in stage.iterdir() if p.is_file())
    require(paths and all(p.stat().st_size > 0 for p in paths), "Empty release asset")
    name = "SHA256SUMS" if kind == "worldchunks" else "SHA256SUMS.txt"
    (stage / name).write_text("".join(sha(p) + "  " + p.name + "\n" for p in paths), encoding="utf-8")
    checksums(stage, name)
    return sorted(p for p in stage.iterdir() if p.is_file())


def api(repo, suffix, *, missing_ok=False, method="GET", fields=None):
    args = ["gh", "api", f"repos/{repo}/{suffix}", "--method", method]
    for key, value in (fields or {}).items():
        args.extend(["-f", f"{key}={value}"])
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode:
        if missing_ok and "404" in result.stderr:
            return None
        raise RuntimeError(result.stderr)
    return json.loads(result.stdout) if result.stdout.strip() else None


def main():
    config = read(ROOT / ".github/release-approval.json")
    repo = os.environ["GITHUB_REPOSITORY"]
    require(os.environ.get("GITHUB_REF") == "refs/heads/main", "Publish only from main")
    metadata = read(ROOT / "SOURCE_RELEASE.json") if config["kind"] != "worldchunks" else None
    if metadata and metadata.get("version") != config["version"]:
        print("This version has no matching release approval; skipping.")
        return
    existing = api(repo, "releases/tags/" + config["tag"], missing_ok=True)
    if existing and not existing["draft"]:
        require(existing["prerelease"] is False, "Existing release is a prerelease")
        print("Stable release already exists; preserving its assets:", existing["html_url"])
        return
    parents = run("git", "rev-list", "--parents", "-n", "1", "HEAD").split()
    source = parents[2] if len(parents) == 3 else parents[0]
    require(run("git", "rev-parse", "HEAD^{tree}") == run("git", "rev-parse", source + "^{tree}"), "Merged tree differs from the tested source")
    run("git", "merge-base", "--is-ancestor", source, "origin/main")
    deadline = time.monotonic() + 1800
    qualified = None
    while time.monotonic() < deadline:
        data = api(repo, f"actions/workflows/{config['workflow']}/runs?head_sha={source}&event=push&per_page=50")
        runs = [r for r in data["workflow_runs"] if r["head_sha"] == source and r["event"] == "push"]
        if runs:
            latest = max(runs, key=lambda r: r["id"])
            if latest["status"] == "completed":
                require(latest["conclusion"] == "success", "Source CI did not pass")
                qualified = latest
                break
        print("Waiting for the exact source CI run to complete.", flush=True)
        time.sleep(15)
    require(qualified is not None, "No successful source CI run available")
    incoming = ROOT / "release-inputs"
    for name in config["artifacts"]:
        run("gh", "run", "download", str(qualified["id"]), "--repo", repo, "--name", name, "--dir", str(incoming / name))
    stage = ROOT / "release-assets"
    files = prepare(config, incoming, source, stage)
    tag = api(repo, "git/ref/tags/" + config["tag"], missing_ok=True)
    if tag:
        obj = tag["object"]
        while obj["type"] == "tag":
            obj = api(repo, "git/tags/" + obj["sha"])["object"]
        require(obj["type"] == "commit" and obj["sha"] == source, "Existing tag points elsewhere")
    else:
        api(repo, "git/refs", method="POST", fields={"ref": "refs/tags/" + config["tag"], "sha": source})
    notes = (ROOT / "RELEASE_NOTES_0.11.16.md").read_text(encoding="utf-8")
    notes += f"\nQualified source: `{source}`.\n\n[Successful build and qualification]({qualified['html_url']}).\n"
    note_path = ROOT / "release-notes.txt"
    note_path.write_text(notes, encoding="utf-8")
    if not existing:
        run("gh", "release", "create", config["tag"], "--repo", repo, "--verify-tag", "--draft", "--title", config["title"], "--notes-file", str(note_path))
    release = api(repo, "releases/tags/" + config["tag"])
    assets = {a["name"]: a for a in release["assets"]}
    expected = {p.name: p for p in files}
    require(set(assets) <= set(expected), "Draft has unexpected assets")
    for name, asset in assets.items():
        require(asset.get("digest") == "sha256:" + sha(expected[name]), f"Existing draft asset differs: {name}")
    missing = [str(p) for p in files if p.name not in assets]
    if missing:
        run("gh", "release", "upload", config["tag"], *missing, "--repo", repo)
    release = api(repo, "releases/tags/" + config["tag"])
    require({a["name"] for a in release["assets"]} == set(expected), "Incomplete release upload")
    for asset in release["assets"]:
        path = expected[asset["name"]]
        require(asset["size"] == path.stat().st_size and asset.get("digest") == "sha256:" + sha(path), "Uploaded bytes differ: " + path.name)
    run("gh", "release", "edit", config["tag"], "--repo", repo, "--draft=false", "--prerelease=false", "--latest")
    release = api(repo, "releases/tags/" + config["tag"])
    require(not release["draft"] and not release["prerelease"], "Release was not published")
    print("Published", release["html_url"], flush=True)


if __name__ == "__main__":
    main()
