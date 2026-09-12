import zipfile
import unittest
from pathlib import Path

from pluginmatrix.preflight import PreflightError, inspect_plugin


def make_plugin(path: Path, plugin_yml: str, main: str = "example.Main") -> None:
    with zipfile.ZipFile(path, "w") as jar:
        jar.writestr("plugin.yml", plugin_yml)
        jar.writestr(main.replace(".", "/") + ".class", b"\xca\xfe\xba\xbe\x00\x00\x00\x00\x00\x00\x00\x3d")


class PreflightTests(unittest.TestCase):
    def test_preflight_reads_block_dependencies(self):
        plugin = Path(self._testMethodName + ".jar")
        make_plugin(
            plugin,
        """name: Example
version: 1.0.0
main: example.Main
softdepend:
  - Vault
  - WorldGuard
api-version: '1.20'
""",
        )
        try:
            metadata, checks = inspect_plugin(plugin)
            self.assertEqual(metadata["plugin_name"], "Example")
            self.assertEqual(metadata["softdepend"], ["Vault", "WorldGuard"])
            self.assertTrue(any(check.name == "main class" and check.status == "PASS" for check in checks))
        finally:
            plugin.unlink(missing_ok=True)

    def test_preflight_reports_missing_descriptor(self):
        plugin = Path(self._testMethodName + ".jar")
        with zipfile.ZipFile(plugin, "w") as jar:
            jar.writestr("example/Main.class", b"\xca\xfe\xba\xbe")
        try:
            with self.assertRaises(PreflightError) as error:
                inspect_plugin(plugin)
            self.assertEqual(error.exception.state, "PLUGIN_LOAD_FAILED")
            self.assertTrue(any(check.name == "plugin.yml" and check.status == "FAIL" for check in error.exception.checks))
        finally:
            plugin.unlink(missing_ok=True)
