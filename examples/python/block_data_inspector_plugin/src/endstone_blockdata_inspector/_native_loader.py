"""Register the exact native provider bundled with the Python bridge."""
from pathlib import Path
import hashlib
import json

from endstone.plugin import Plugin
from endstone_blockdata import __version__


class BlockDataNativeBundle(Plugin):
    api_version = "0.11"
    load = "STARTUP"
    # This makes dependencies resolvable before on_load installs the provider.
    # The native plugin retains the actual blockdata_api registration.
    provides = ["blockdata_api"]

    def on_load(self):
        manager = self.server.plugin_manager
        existing = manager.get_plugin("blockdata_api")
        if existing is not None:
            found = existing.description.version
            if found != __version__:
                raise RuntimeError(
                    f"BlockData native plugin {found} does not match bridge {__version__}. "
                    "Remove the older native plugin and install the matching bundle wheel."
                )
            return
        native = Path(__file__).parent / "native"
        manifest = json.loads((native / "manifest.json").read_text(encoding="utf-8"))
        name = manifest["filename"]
        if Path(name).name != name or manifest["version"] != __version__:
            raise RuntimeError("Invalid BlockData native bundle manifest")
        path = native / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["sha256"]:
            raise RuntimeError("BlockData native bundle checksum mismatch; reinstall the release wheel")
        if manager.load_plugin(str(path.resolve())) is None:
            raise RuntimeError("Could not load bundled BlockData native provider; check the preceding native loader error")
