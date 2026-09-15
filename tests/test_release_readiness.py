import hashlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from pluginmatrix import __version__
from pluginmatrix.preflight import inspect_plugin
from standalone import build as standalone_build


ROOT = Path(__file__).resolve().parents[1]


class ReleaseReadinessTests(unittest.TestCase):
    def test_version_has_one_authoritative_literal(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        package_init = (ROOT / "pluginmatrix" / "__init__.py").read_text(encoding="utf-8")
        self.assertEqual(__version__, "0.9.0")
        self.assertIn('dynamic = ["version"]', pyproject)
        self.assertIn('version = {attr = "pluginmatrix.__version__"}', pyproject)
        self.assertNotIn('version = "0.5.1"', pyproject)
        self.assertIn('__version__ = "0.9.0"', package_init)

    def test_required_open_source_files_and_templates_exist(self):
        required = (
            "LICENSE",
            "CHANGELOG.md",
            "CODE_OF_CONDUCT.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "THIRD_PARTY_NOTICES.md",
            "docs/RELEASE_CHECKLIST.md",
            "docs/PUBLISHING.md",
            "docs/VERSIONING.md",
            "standalone/pluginmatrix.spec",
            "standalone/build.py",
            "standalone/licenses/CPYTHON-LICENSE.txt",
            "standalone/licenses/NATIVE-LICENSES.txt",
            ".github/workflows/standalone.yml",
            ".github/ISSUE_TEMPLATE/bug_report.yml",
            ".github/ISSUE_TEMPLATE/feature_request.yml",
            ".github/pull_request_template.md",
        )
        for relative in required:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_standalone_builder_has_an_offline_cpython_license_fallback(self):
        fallback = standalone_build.python_license(())
        self.assertEqual(fallback, ROOT / "standalone" / "licenses" / "CPYTHON-LICENSE.txt")
        text = fallback.read_text(encoding="utf-8")
        self.assertIn("PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2", text)
        self.assertIn("CWI LICENSE AGREEMENT FOR PYTHON 0.9.0 THROUGH 1.2", text)

        native = (ROOT / "standalone" / "licenses" / "NATIVE-LICENSES.txt").read_text(
            encoding="utf-8"
        )
        for dependency in ("OpenSSL 3", "bzip2", "libffi", "liblzma", "libuuid", "zlib"):
            self.assertIn(dependency, native)
        self.assertIn("Apache License 2.0", native)
        self.assertIn("Redistributions in binary form", native)

        notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        self.assertIn("official Eclipse Adoptium API", notices)
        self.assertIn("GPLv2 with the Classpath Exception", notices)
        self.assertIn("never included in the PluginMatrix wheel", notices)

    def test_collaboration_templates_request_actionable_diagnostics(self):
        bug = (ROOT / ".github/ISSUE_TEMPLATE/bug_report.yml").read_text(encoding="utf-8")
        for value in (
            "PluginMatrix version",
            "Operating system",
            "Python version",
            "Java/JDK version",
            "Minecraft/Paper version",
            "fixed Paper build",
            "verdict",
            "failure_stage",
            "Matrix Report",
            "runtime result",
            "server.log",
            "reproduces consistently",
            "sensitive",
            "third-party JAR",
        ):
            with self.subTest(value=value):
                self.assertIn(value, bug)
        pull_request = (ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")
        self.assertIn("python -m unittest discover -s tests -v", pull_request)
        self.assertIn("third-party", pull_request)
        self.assertIn("GPL-3.0", pull_request)

    def test_owned_fixtures_are_traceable_and_match_checksums(self):
        checksum_lines = (ROOT / "ci-fixtures" / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
        expected = dict(line.split(maxsplit=1)[::-1] for line in checksum_lines if line.strip())
        self.assertEqual(set(expected), {"PluginMatrixSmoke.jar", "PluginMatrixEnableFailure.jar"})
        self.assertFalse((ROOT / "ci-fixtures" / "EnhancedFly-2.2.0.jar").exists())
        for filename, plugin_name, source_dir in (
            ("PluginMatrixSmoke.jar", "PluginMatrixSmoke", "smoke"),
            ("PluginMatrixEnableFailure.jar", "PluginMatrixEnableFailure", "enable-failure"),
        ):
            with self.subTest(filename=filename):
                jar = ROOT / "ci-fixtures" / filename
                digest = hashlib.sha256(jar.read_bytes()).hexdigest()
                self.assertEqual(digest, expected[filename])
                metadata, _ = inspect_plugin(jar)
                self.assertEqual(metadata["plugin_name"], plugin_name)
                self.assertTrue((ROOT / "ci-fixtures" / source_dir / "plugin.yml").is_file())
                self.assertTrue(any((ROOT / "ci-fixtures" / source_dir / "src").rglob("*.java")))
                with zipfile.ZipFile(jar) as archive:
                    self.assertEqual(
                        sorted(archive.namelist()),
                        sorted(
                            [
                                f"pluginmatrix/fixture/{'SmokePlugin' if source_dir == 'smoke' else 'EnableFailurePlugin'}.class",
                                "plugin.yml",
                            ]
                        ),
                    )
        build_script = (ROOT / "ci-fixtures" / "build_fixtures.py").read_text(encoding="utf-8")
        self.assertIn('"--paper-jar"', build_script)
        self.assertIn('"--release", "17"', build_script)

    def test_readme_commands_and_paths_match_cli(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for value in (
            "python -m pluginmatrix test",
            "python -m pluginmatrix matrix .\\examples\\matrix.json",
            "pluginmatrix --version",
            "pipx install pluginmatrix",
            "pipx upgrade pluginmatrix",
            "https://pypi.org/project/pluginmatrix/0.9.0/",
            ".pluginmatrix/cache",
            ".pluginmatrix/runs",
            "result.json",
            "server.log",
            "matrix-report.json",
            "examples/ci-matrix.json",
            "examples/ci-enable-failure-matrix.json",
            "examples/behavior.json",
            "examples/behavior-matrix.json",
            "python -m unittest discover -s tests -v",
        ):
            with self.subTest(value=value):
                self.assertIn(value, readme)

    def test_sdist_and_wheel_exclude_local_and_binary_artifacts(self):
        ignored = shutil.ignore_patterns(
            ".git",
            ".pluginmatrix",
            ".serena",
            ".venv",
            "venv",
            "build",
            "dist",
            "*.egg-info",
            "__pycache__",
            "*.pyc",
        )
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            checkout = temporary_path / "checkout"
            shutil.copytree(ROOT, checkout, ignore=ignored)
            output = temporary_path / "dist"
            output.mkdir()
            completed = subprocess.run(
                [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(output), str(checkout)],
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            sdist_name = next(path.name for path in output.iterdir() if path.name.endswith(".tar.gz"))
            wheel_name = next(path.name for path in output.iterdir() if path.name.endswith(".whl"))

            with tarfile.open(output / sdist_name, "r:gz") as archive:
                sdist_entries = [name.replace("\\", "/") for name in archive.getnames()]
            with zipfile.ZipFile(output / wheel_name) as archive:
                wheel_entries = [name.replace("\\", "/") for name in archive.namelist()]
                metadata_name = next(name for name in wheel_entries if name.endswith(".dist-info/METADATA"))
                metadata = archive.read(metadata_name).decode("utf-8")

            banned = ("/.pluginmatrix/", "/__pycache__/", ".pyc", "/build/", "/dist/", "/.venv/", "EnhancedFly", ".jar")
            for entries in (sdist_entries, wheel_entries):
                for entry in entries:
                    normalized = f"/{entry}"
                    self.assertFalse(any(token in normalized for token in banned), entry)
            self.assertTrue(any(name.endswith("/README.md") for name in sdist_entries))
            self.assertTrue(any(name.endswith("/LICENSE") for name in sdist_entries))
            self.assertTrue(any(name.endswith("/examples/matrix.json") for name in sdist_entries))
            self.assertTrue(any(name.endswith("/ci-fixtures/smoke/plugin.yml") for name in sdist_entries))
            self.assertTrue(any(name.endswith("/standalone/licenses/CPYTHON-LICENSE.txt") for name in sdist_entries))
            self.assertTrue(any(name.endswith("/standalone/licenses/NATIVE-LICENSES.txt") for name in sdist_entries))
            self.assertTrue(any(name == "pluginmatrix/cli.py" for name in wheel_entries))
            self.assertTrue(any(name == "pluginmatrix/webui/index.html" for name in wheel_entries))
            self.assertTrue(any(name == "pluginmatrix/webui/app.js" for name in wheel_entries))
            self.assertFalse(any(name.startswith("tests/") for name in wheel_entries))
            self.assertIn("Name: pluginmatrix", metadata)
            self.assertIn(f"Version: {__version__}", metadata)
            self.assertIn("Summary: Real server runtime verification for Minecraft plugins", metadata)
            self.assertIn("License-Expression: Apache-2.0", metadata)
            self.assertIn("License-File: LICENSE", metadata)
            self.assertIn("Requires-Python: >=3.10", metadata)
            self.assertIn("Project-URL: Repository, https://github.com/YouDaoRS/PluginMatrix", metadata)


if __name__ == "__main__":
    unittest.main()
