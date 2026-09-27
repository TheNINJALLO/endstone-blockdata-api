from importlib.util import module_from_spec, spec_from_file_location
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class NativeBundleTests(unittest.TestCase):
    def load(self):
        plugin_module = ModuleType('endstone.plugin')
        plugin_module.Plugin = object
        api_module = ModuleType('endstone_blockdata')
        api_module.__version__ = '0.6.6'
        source = Path(__file__).parents[2] / 'examples/python/block_data_inspector_plugin/src/endstone_blockdata_inspector/_native_loader.py'
        spec = spec_from_file_location('bundle_under_test', source)
        module = module_from_spec(spec)
        with patch.dict('sys.modules', {'endstone.plugin': plugin_module, 'endstone_blockdata': api_module}):
            spec.loader.exec_module(module)
        plugin = module.BlockDataNativeBundle()
        manager = SimpleNamespace(get_plugin=Mock(return_value=None), load_plugin=Mock(return_value=object()))
        plugin.server = SimpleNamespace(plugin_manager=manager)
        return module, plugin, manager

    def test_bundle_declares_provider_and_loads_verified_native_file(self):
        module, plugin, manager = self.load()
        self.assertEqual(plugin.provides, ['blockdata_api'])
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            native = root / 'native'
            native.mkdir()
            payload = native / 'provider.so'
            payload.write_bytes(b'fixture')
            (native / 'manifest.json').write_text(json.dumps({'filename': payload.name, 'version': '0.6.6',
                                                             'sha256': hashlib.sha256(payload.read_bytes()).hexdigest()}))
            module.__file__ = str(root / '_native_loader.py')
            plugin.on_load()
            manager.load_plugin.assert_called_once_with(str(payload.resolve()))

    def test_mismatched_existing_plugin_is_not_reused(self):
        _, plugin, manager = self.load()
        manager.get_plugin.return_value = SimpleNamespace(description=SimpleNamespace(version='0.4.8'))
        with self.assertRaisesRegex(RuntimeError, 'does not match'):
            plugin.on_load()
        manager.load_plugin.assert_not_called()

    def test_matching_existing_plugin_does_not_load_twice(self):
        _, plugin, manager = self.load()
        manager.get_plugin.return_value = SimpleNamespace(description=SimpleNamespace(version='0.6.6'))
        plugin.on_load()
        manager.load_plugin.assert_not_called()

    def test_modified_binary_is_rejected_before_native_loading(self):
        module, plugin, manager = self.load()
        with TemporaryDirectory() as temporary:
            native = Path(temporary) / 'native'
            native.mkdir()
            (native / 'provider.so').write_bytes(b'changed')
            (native / 'manifest.json').write_text(json.dumps({'filename': 'provider.so', 'version': '0.6.6', 'sha256': 'bad'}))
            module.__file__ = str(native.parent / '_native_loader.py')
            with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
                plugin.on_load()
            manager.load_plugin.assert_not_called()
