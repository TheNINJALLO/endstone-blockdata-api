"""Register the exact native provider bundled with the Python bridge."""
from pathlib import Path
import hashlib
import json



def load_native_provider(plugin):
    version = plugin.version
    manager = plugin.server.plugin_manager
    existing = manager.get_plugin("blockdata_api")
    if existing is not None:
        found = existing.description.version
        if found != version:
            raise RuntimeError(
                f"BlockData native plugin {found} does not match bridge {version}. "
                "Remove the older native plugin and install the matching bundle wheel."
            )
        return
    native = Path(__file__).parent / "native"
    manifest = json.loads((native / "manifest.json").read_text(encoding="utf-8"))
    name = manifest["filename"]
    if Path(name).name != name or manifest["version"] != version:
        raise RuntimeError("Invalid BlockData native bundle manifest")
    path = native / name
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["sha256"]:
        raise RuntimeError("BlockData native bundle checksum mismatch; reinstall the release wheel")
    if manager.load_plugin(str(path.resolve())) is None:
        raise RuntimeError("Could not load bundled BlockData native provider; check the preceding native loader error")
