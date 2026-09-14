import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from standalone.build import archive_bundle
from standalone.entrypoint import main as standalone_main


class StandaloneAssetTests(unittest.TestCase):
    def test_windows_double_click_starts_web_and_reports_startup_failure(self):
        with patch.dict('os.environ', {'PLUGINMATRIX_NO_BROWSER': '1'}), \
             patch('pluginmatrix.web.serve', return_value=0) as serve:
            self.assertEqual(standalone_main([], platform_name='nt'), 0)
        state_dir = serve.call_args.kwargs['state_dir']
        self.assertEqual(state_dir.name, 'web')
        self.assertEqual(state_dir.parent.name, 'PluginMatrix')
        self.assertEqual(serve.call_args.kwargs['port'], 0)
        self.assertFalse(serve.call_args.kwargs['open_browser'])
        with patch('pluginmatrix.web.serve', side_effect=OSError('port unavailable')), \
             patch('standalone.entrypoint._show_windows_error') as message:
            self.assertEqual(standalone_main([], platform_name='nt'), 2)
        self.assertIn('pluginmatrix.exe web --port 0', message.call_args.args[0])

    def test_runtime_and_private_assets_are_rejected_before_archive_creation(self):
        for name in ("plugin.JAR", "server.log", "progress.jsonl", "cache/data", ".env",
                     ".env.local", ".aws/credentials", "secret.pem", "key.pfx", "runs/report.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                bundle = root / "bundle"
                asset = bundle / name
                asset.parent.mkdir(parents=True)
                asset.write_bytes(b"must not be distributed")
                archive = root / "bundle.zip"
                with self.assertRaises(RuntimeError):
                    archive_bundle(bundle, archive, "windows")
                self.assertFalse(archive.exists())

    def test_clean_assets_archive_normally(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            bundle.mkdir()
            (bundle / "LICENSE").write_text("license", encoding="utf-8")
            archive = root / "bundle.zip"
            archive_bundle(bundle, archive, "windows")
            with zipfile.ZipFile(archive) as saved:
                self.assertEqual(saved.namelist(), ["bundle/LICENSE"])

    def test_external_symlink_cannot_enter_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = root / "bundle"
            bundle.mkdir()
            secret = root / "secret.txt"
            secret.write_text("secret", encoding="utf-8")
            try:
                (bundle / "library").symlink_to(secret)
            except OSError:
                self.skipTest("symlink creation unavailable")
            archive = root / "bundle.tar.gz"
            with self.assertRaises(RuntimeError):
                archive_bundle(bundle, archive, "linux")
            self.assertFalse(archive.exists())
