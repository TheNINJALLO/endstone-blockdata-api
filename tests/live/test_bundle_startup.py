"""Qualify the release bundle's live writes, nested items and persisted restart."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("wheel", type=Path)
parser.add_argument("--server", type=Path, required=True)
args = parser.parse_args()
server = args.server.resolve()
server.mkdir(exist_ok=False)
plugins = server / "plugins"
plugins.mkdir()
shutil.copy2(args.wheel, plugins / args.wheel.name)
result = server / "probe.json"
mode = server / "probe-mode.txt"
adapter_url = "https://raw.githubusercontent.com/TheNINJALLO/endstone-antigrief/8c743f6c5b485fafca75f2c9ba0dfd1036860c39/src/endstone_antigrief/blockdata_adapter.py"
adapter = urllib.request.urlopen(adapter_url, timeout=30).read()
assert hashlib.sha256(adapter).hexdigest() == "85e7c3b4fc3f6388b5e306ef6580eba97b7b505463e9e9367046cd9d6a490180"
source = (Path(__file__).parent / "bundle_probe.py").read_text(encoding="utf-8")
source = source.replace("__RESULT_PATH__", repr(str(result))).replace("__MODE_PATH__", repr(str(mode)))
with ZipFile(plugins / "endstone_bundle_probe-1.0.0-py3-none-any.whl", "w") as archive:
    archive.writestr("bundle_probe.py", source)
    archive.writestr("bundle_probe_adapter.py", adapter)
    info = "endstone_bundle_probe-1.0.0.dist-info/"
    archive.writestr(info + "METADATA", "Metadata-Version: 2.1\nName: endstone-bundle-probe\nVersion: 1.0.0\n")
    archive.writestr(info + "WHEEL", "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
    archive.writestr(info + "entry_points.txt", "[endstone]\nbundle-probe = bundle_probe:Probe\n")
    archive.writestr(info + "RECORD", "")
(server / "server.properties").write_text(
    "server-name=BlockData bundle acceptance\nlevel-name=bundle-test\nonline-mode=false\n"
    "allow-list=false\nallow-cheats=true\nenable-script=true\nenable-lan-visibility=false\n"
    "server-port=39461\nserver-portv6=39462\nview-distance=4\ntick-distance=4\nlevel-type=FLAT\ntransport=nethernet\n",
    encoding="utf-8",
)
(server / "endstone.toml").write_text("[settings]\n", encoding="utf-8")
reports = []
for phase in ("write", "verify"):
    mode.write_text(phase, encoding="utf-8")
    result.unlink(missing_ok=True)
    log_path = server / f"server-{phase}.log"
    with log_path.open("w", encoding="utf-8") as log:
        env = os.environ.copy()
        env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env["PATH"]
        process = subprocess.Popen(
            [sys.executable, "-m", "endstone", "--server-folder", str(server), "--yes"],
            cwd=server, env=env, stdin=subprocess.PIPE, stdout=log,
            stderr=subprocess.STDOUT, text=True,
        )
        try:
            deadline = time.monotonic() + 240
            while time.monotonic() < deadline and process.poll() is None and not result.exists():
                time.sleep(0.2)
            assert result.exists(), log_path.read_text(encoding="utf-8", errors="replace")[-16000:]
            report = json.loads(result.read_text(encoding="utf-8"))
            assert report["passed"], report
            reports.append(report)
        finally:
            if process.poll() is None:
                process.stdin.write("stop\n")
                process.stdin.flush()
                try:
                    process.wait(timeout=40)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            assert process.returncode == 0, process.returncode
    shutil.copyfile(log_path, server / "server.log")
runtime = Path(importlib.util.find_spec("endstone").origin).parent / "libendstone_runtime.so"
subprocess.run([sys.executable, str(ROOT / "scripts/verify_native_binary.py"),
                "--profile", str(ROOT / "compatibility/native-binary-profile-0.11.16-linux-x64.json"),
                "--bds", str(server / "bedrock_server"), "--endstone-runtime", str(runtime)], check=True)
report = {"passed": True, "endstone": "0.11.16", "bds": "1.26.65.1",
          "wheel_sha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
          "persisted_restart": True, "clean_shutdown": True, "connected_client_tested": False,
          "phases": reports}
result.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(result.read_text(encoding="utf-8"))
