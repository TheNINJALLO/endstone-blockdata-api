"""Start a disposable BDS using only the release bundle wheel and a dependent probe."""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from zipfile import ZipFile
p=argparse.ArgumentParser();p.add_argument("wheel",type=Path);p.add_argument("--server",type=Path,required=True);a=p.parse_args()
server=a.server.resolve();server.mkdir(exist_ok=False);plugins=server/"plugins";plugins.mkdir();shutil.copy2(a.wheel,plugins/a.wheel.name)
result=server/"probe.json"
source=f'''from pathlib import Path
import json
from endstone.plugin import Plugin
class Probe(Plugin):
    api_version="0.11"
    depend=["blockdata_api"]
    def on_enable(self):
        self.server.scheduler.run_task(self,self.check,delay=40)
    def check(self):
        from endstone_blockdata_inspector import _endstone_blockdata_live as bridge
        native=self.server.plugin_manager.get_plugin("blockdata_api")
        available=bridge.available()
        result={{"available":available,"native_version":native.description.version,"bridge_version":bridge.__version__,"capabilities":bridge.capabilities()}}
        result["passed"]=available and native.description.version==bridge.__version__=="0.6.6"
        Path({str(result)!r}).write_text(json.dumps(result,indent=2))
'''
with ZipFile(plugins/"endstone_bundle_probe-1.0.0-py3-none-any.whl","w") as z:
    z.writestr("bundle_probe.py",source)
    info="endstone_bundle_probe-1.0.0.dist-info/"
    z.writestr(info+"METADATA","Metadata-Version: 2.1\nName: endstone-bundle-probe\nVersion: 1.0.0\n")
    z.writestr(info+"WHEEL","Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
    z.writestr(info+"entry_points.txt","[endstone]\nbundle-probe = bundle_probe:Probe\n")
    z.writestr(info+"RECORD","")
(server/"server.properties").write_text("server-name=BlockData bundle acceptance\nlevel-name=bundle-test\nonline-mode=false\nserver-port=39461\nserver-portv6=39462\nview-distance=4\ntick-distance=4\nlevel-type=FLAT\ntransport=nethernet\n")
(server/"endstone.toml").write_text("[settings]\n")
with (server/"server.log").open("w") as log:
    env=os.environ.copy();env["PATH"]=str(Path(sys.executable).parent)+os.pathsep+env["PATH"]
    process=subprocess.Popen([sys.executable,"-m","endstone","--server-folder",str(server),"--yes"],cwd=server,env=env,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,text=True)
    try:
        deadline=time.monotonic()+240
        while time.monotonic()<deadline and process.poll() is None:
            if result.exists():break
            time.sleep(.2)
        assert result.exists(), (server/"server.log").read_text()[-16000:]
        report=json.loads(result.read_text());assert report["passed"],report
        report["wheel_sha256"]=hashlib.sha256(a.wheel.read_bytes()).hexdigest()
        result.write_text(json.dumps(report,indent=2));print(result.read_text())
    finally:
        if process.poll() is None:
            process.stdin.write("stop\n");process.stdin.flush()
            try:process.wait(timeout=40)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        assert process.returncode==0,process.returncode
