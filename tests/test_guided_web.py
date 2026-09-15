import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pluginmatrix import application
from pluginmatrix.cli import main
from pluginmatrix.files import atomic_json
from pluginmatrix.locking import file_lock
from pluginmatrix.web import WebApplication
from test_guided import make_plugin


class GuidedWebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.jar = make_plugin(self.root / "Example.jar", extra="commands:\n  ping:\n    description: Ping\n")
        self.app = WebApplication(self.root / "web", self.root / "cache")
        self.addCleanup(self.app.close)

    def document(self, **extra):
        return {"schema": 2, "profile": {"id": "standard", "revision": 1}, "plugin": str(self.jar),
                "environments": [{"server": {"type": "paper", "version": "1.20.1", "build": 196}, "java": "17"}],
                "options": {"jdk_dir": str(self.root / "jdks")}, **extra}

    @unittest.skipUnless(os.name == "nt", "Windows 8.3 path aliases")
    def test_windows_short_path_alias_is_canonicalized(self):
        import ctypes
        directory = self.root / "Long directory name for short path"
        directory.mkdir()
        buffer = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetShortPathNameW(str(directory), buffer, len(buffer))
        if not length or length >= len(buffer) or buffer.value == str(directory):
            self.skipTest("8.3 aliases unavailable on this filesystem")
        app = WebApplication(Path(buffer.value) / "web", Path(buffer.value) / "cache")
        self.addCleanup(app.close)
        self.assertEqual(app.state_dir, (directory / "web").resolve())
        self.assertEqual(app.cache_dir, (directory / "cache").resolve())

    def test_guided_import_export_preserves_profile_managed_id_options_and_edited_behavior(self):
        ident = "temurin-17-windows-x64-" + "a" * 64
        document = self.document(behavior={"schema": 1, "checks": [
            {"id": "edited", "type": "wait", "seconds": 1, "timeout": 3}]})
        document["environments"][0]["java"] = {"managed": ident}
        document["options"].update(timeout=234, stability_window=18, max_parallel=2,
                                   html_report=str(self.root / "custom.html"))
        source = self.root / "matrix.json"
        source.write_text(json.dumps(document), encoding="utf-8")
        imported = self.app.import_configuration(str(source))["configuration"]
        exported = self.app.generate_configuration({"configuration": imported})
        self.assertEqual(exported, imported)
        self.assertEqual(exported["environments"][0]["java"], {"managed": ident})
        self.assertEqual(exported["behavior"]["checks"][0]["id"], "edited")
        self.assertEqual(exported["options"]["jdk_dir"], str((self.root / "jdks").resolve()))
        with patch("pluginmatrix.web.application.run_configuration", return_value={
            "summary": {"total": 1, "passed": 0, "failed": 1}, "environments": []}) as run:
            job = self.app.submit({"configuration": exported})
            job.thread.join(5)
        self.assertEqual(run.call_args.args[0]["profile"], imported["profile"])
        self.assertEqual(run.call_args.args[0]["behavior"], imported["behavior"])
        self.assertEqual(job.configuration, exported)
        self.assertNotEqual(run.call_args.args[0]["options"]["report"], exported["options"]["report"])

    def test_unknown_fields_duplicate_json_and_profile_revision_fail_closed(self):
        for change in ({"schema": 3}, {"profile": {"id": "standard", "revision": 2}}, {"surprise": True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.app.generate_configuration({"configuration": self.document(**change)})
        raw = json.dumps(self.document()).replace('"schema": 2', '"schema": 2, "schema": 1')
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.app.normalize_configuration({"configuration": raw})

    def test_prepare_uses_core_suggestions_only_once_and_respects_explicit_checks(self):
        payload = {"plugin": str(self.jar), "environments": self.document()["environments"], "profile": "standard"}
        first = self.app.guided("prepare", payload)
        self.assertEqual(first["configuration"]["behavior"]["checks"][0]["type"], "command_registered")
        payload["behavior"] = {"schema": 1, "checks": [{"id": "edited", "type": "wait", "seconds": 1}]}
        edited = self.app.guided("prepare", payload)["configuration"]
        self.assertEqual([c["id"] for c in edited["behavior"]["checks"]], ["edited"])
        self.assertEqual(self.app.generate_configuration({"configuration": edited}), edited)
        del payload["behavior"]
        payload["use_suggestions"] = False
        self.assertNotIn("behavior", self.app.guided("prepare", payload)["configuration"])

    def test_project_retains_uploaded_inputs_across_restart(self):
        data = self.jar.read_bytes()
        imported = self.app.import_file(io.BytesIO(data), len(data), "Example.jar", "plugin")
        normalized = self.app.normalize_configuration({"configuration": self.document(plugin={"file_id": imported["file_id"]})})["configuration"]
        project = self.app.save_project({"name": "Local project", "configuration": normalized})
        copied = Path(project["configuration"]["plugin"])
        self.assertTrue(copied.is_relative_to(self.app.state_dir / "inputs"))
        self.app.close()
        self.assertEqual(copied.read_bytes(), data)
        restarted = WebApplication(self.app.state_dir, self.app.cache_dir)
        self.addCleanup(restarted.close)
        self.assertEqual(restarted.list_projects()[0], project)
        self.assertEqual(restarted.generate_configuration({"configuration": project["configuration"]}), project["configuration"])

    def test_finished_history_restores_identity_and_rejects_modified_artifact(self):
        def execute(document, **kwargs):
            path = Path(document["options"]["report"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"original": true}', encoding="utf-8")
            return {"summary": {"total": 1, "passed": 1, "failed": 0}, "environments": [{
                "runtime_verdict": "PASS", "verdict": "PASS", "verification_passed": True,
                "behavior": {"verdict": "NOT_RUN"}, "artifacts": {}}]}
        with patch("pluginmatrix.web.application.run_configuration", side_effect=execute):
            job = self.app.submit({"configuration": self.document()})
            job.thread.join(5)
        self.assertEqual(job.status, "completed", job.error)
        self.app.close()
        restarted = WebApplication(self.app.state_dir, self.app.cache_dir)
        self.addCleanup(restarted.close)
        restored = restarted.get_job(job.id)
        self.assertEqual(restored.configuration_sha256, job.configuration_sha256)
        artifact_id = next(iter(restored.artifacts))
        artifact, stream = restarted.artifact(job.id, artifact_id)
        stream.close()
        artifact.path.write_text('{"changed": true}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed"):
            restarted.artifact(job.id, artifact_id)

    def test_failure_subset_preserves_checks_and_drops_only_invalid_matrix_profile(self):
        document = self.document(profile={"id": "matrix", "revision": 1},
                                 behavior={"schema": 1, "checks": [{"id": "keep", "type": "wait", "seconds": 1}]})
        document["environments"].append({"server": {"type": "paper", "version": "1.20.4", "build": 499}, "java": "17"})
        report = {"summary": {"total": 2, "passed": 1, "failed": 1}, "environments": [
            {"verdict": "PASS", "verification_passed": True, "artifacts": {}},
            {"verdict": "PASS", "verification_passed": False, "behavior": {"verdict": "FAIL"}, "artifacts": {}}]}
        with patch("pluginmatrix.web.application.run_configuration", return_value=report):
            job = self.app.submit({"configuration": document})
            job.thread.join(5)
        restored = self.app.retry_configuration(job.id, failed_only=True)
        self.assertEqual(len(restored["configuration"]["environments"]), 1)
        self.assertEqual(restored["configuration"]["environments"][0]["server"]["build"], 499)
        self.assertNotIn("profile", restored["configuration"])
        self.assertEqual(restored["configuration"]["behavior"]["checks"][0]["id"], "keep")
        self.assertEqual(job.configuration["profile"]["id"], "matrix")
        self.jar.write_bytes(b"changed")
        self.assertEqual(self.app.retry_configuration(job.id)["changed_sources"], [str(self.jar.resolve())])

    def test_cache_operation_uses_application_and_cancellation(self):
        import threading
        started = threading.Event()
        def install(*args, control=None, **kwargs):
            started.set()
            while not control.cancelled:
                control._cancelled.wait(.01)
            control.check()
        with patch("pluginmatrix.web.application.install_managed_jdk", side_effect=install):
            job = self.app.maintenance("jdk-install", {"major": 17, "id": "reviewed"})
            self.assertTrue(started.wait(2))
            self.app.cancel(job.id)
            job.thread.join(3)
        self.assertEqual(job.status, "cancelled")

    def test_cache_deletion_is_id_based_locked_and_retains_unowned_files(self):
        from pluginmatrix.files import sha256_file
        cache = self.app.cache_dir
        jar = cache / "paper" / "1.20.1" / "196" / "paper-1.20.1-196.jar"
        jar.parent.mkdir(parents=True)
        jar.write_bytes(b"test-owned cache")
        receipt = jar.with_name(jar.name + ".sha256.json")
        atomic_json(receipt, {"sha256": sha256_file(jar)})
        unrelated = jar.parent / "keep.txt"; unrelated.write_text("do not delete")
        entry = application.inspect_server_cache(cache)["entries"][0]
        self.assertEqual(application.manage_server_cache(entry["id"], root=cache)["integrity"], "verified")
        lock = jar.with_name(jar.name + ".lock")
        with file_lock(lock, timeout=0), self.assertRaises(TimeoutError):
            application.manage_server_cache(entry["id"], root=cache, delete=True)
        with self.assertRaises(ValueError):
            application.manage_server_cache("../escape", root=cache, delete=True)
        jar.write_bytes(b"corrupt")
        with self.assertRaisesRegex(ValueError, "integrity"):
            application.manage_server_cache(entry["id"], root=cache)
        application.manage_server_cache(entry["id"], root=cache, delete=True)
        self.assertFalse(jar.exists())
        self.assertFalse(receipt.exists())
        self.assertTrue(unrelated.exists())
        self.assertTrue(lock.exists())

    def test_cli_human_and_json_modes_and_init_keep_explicit_behavior(self):
        for args in (["profiles"], ["analyze", "--plugin", str(self.jar)], ["jdk", "list", "--directory", str(self.root / "empty-jdks")]):
            with redirect_stdout(io.StringIO()) as text:
                self.assertEqual(main(args), 0)
            self.assertFalse(text.getvalue().lstrip().startswith("{"))
            with redirect_stdout(io.StringIO()) as text:
                self.assertEqual(main([*args, "--json"]), 0)
            self.assertIsInstance(json.loads(text.getvalue()), dict)
        behavior = self.root / "behavior.json"
        behavior.write_text(json.dumps({"schema": 1, "checks": [{"id": "keep", "type": "wait", "seconds": 1}]}))
        source = self.root / "init.json"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["init", str(source), "--plugin", str(self.jar), "--minecraft", "1.20.1",
                                   "--java", "17", "--profile", "standard", "--behavior", str(behavior),
                                   "--jdk-dir", str(self.root / "jdks")]), 0)
        self.assertEqual(json.loads(source.read_text())["behavior"]["checks"][0]["id"], "keep")


if __name__ == "__main__":
    unittest.main()
