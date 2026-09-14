import http.client
import io
import json
import os
import re
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from pluginmatrix import application
from pluginmatrix.model import VerificationResult
from pluginmatrix.providers import ServerSpec
from pluginmatrix.web import LocalWebServer, WebApplication, WebError
from test_regressions import plugin


class WebApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plugin = plugin(self.root / "plugin.jar")
        self.app = WebApplication(self.root / "state", self.root / "cache")
        self.addCleanup(self.app.close)

    def request(self, mode="single", parallel=1):
        return {
            "mode": mode,
            "plugin": str(self.plugin),
            "dependencies": [],
            "environments": [{"server": {"type": "paper", "version": "1.20.1", "build": 196}, "java": "17"}],
            "options": {"timeout": 120, "stability_window": 5, "max_parallel": parallel},
        }

    def test_generate_and_import_use_core_matrix_configuration(self):
        generated = self.app.generate_configuration(self.request("matrix", 2))
        self.assertEqual(generated["plugin"], str(self.plugin.resolve()))
        self.assertEqual(generated["environments"][0]["server"]["type"], "paper")
        self.assertEqual(generated["options"]["max_parallel"], 2)
        source = self.root / "matrix.json"
        application.init_configuration(
            source,
            plugin=self.plugin,
            servers=[ServerSpec("purpur", "1.21.4")],
            java="21",
        )
        imported = self.app.import_configuration(str(source))["configuration"]
        self.assertEqual(imported["plugin"], str(self.plugin.resolve()))
        self.assertEqual(imported["environments"][0]["server"]["type"], "purpur")

    def test_single_job_uses_application_result_events_and_artifacts(self):
        def fake_run(**kwargs):
            kwargs["control"].emit("server_started", 0, provider="paper")
            run_dir = kwargs["work_root"] / "run-test"
            run_dir.mkdir(parents=True)
            log = run_dir / "server.log"
            log.write_bytes(b"raw server log\n")
            result = VerificationResult(result="PASS", metadata={"server": {"server_type": "paper"}}, workdir=str(run_dir), log_path=str(log))
            application.write_report(result, kwargs["report_path"])
            kwargs["html_path"].write_text("<!doctype html><title>report</title>", encoding="utf-8")
            kwargs["control"].emit("environment_completed", 0, verdict="PASS")
            return result

        with patch("pluginmatrix.web.application.run_single", side_effect=fake_run) as service:
            job = self.app.submit(self.request())
            job.thread.join(timeout=5)
        self.assertFalse(job.thread.is_alive())
        snapshot = job.snapshot()
        self.assertEqual(snapshot["status"], "completed")
        self.assertEqual(snapshot["summary"]["environments"][0]["verdict"], "PASS")
        self.assertEqual([event["kind"] for event in snapshot["events"]], ["server_started", "environment_completed"])
        self.assertEqual({artifact["label"] for artifact in snapshot["artifacts"]}, {"JSON report", "HTML report", "server.log"})
        self.assertIs(service.call_args.kwargs["control"], job.control)

    def test_global_slot_limit_and_cancel_are_shared_with_matrix_control(self):
        started = threading.Event()

        def fake_matrix(config, control):
            started.set()
            while not control.cancelled:
                time.sleep(0.01)
            report = {"summary": {"total": 1, "passed": 0, "failed": 1}, "environments": [{
                "id": "paper", "verdict": "CANCELLED", "failure_stage": "cancelled", "reason": "cancelled",
                "metadata": {"server": {"server_type": "paper"}}, "artifacts": {},
            }]}
            config.report_path.parent.mkdir(parents=True, exist_ok=True)
            config.report_path.write_text(json.dumps(report), encoding="utf-8")
            config.html_path.write_text("<!doctype html>", encoding="utf-8")
            return report

        with patch("pluginmatrix.web.application.run_matrix", side_effect=fake_matrix):
            job = self.app.submit(self.request("matrix", 8))
            self.assertTrue(started.wait(2))
            with self.assertRaisesRegex(WebError, "reserve 8"):
                self.app.submit(self.request())
            self.app.cancel(job.id)
            job.thread.join(timeout=5)
        self.assertTrue(job.control.cancelled)
        self.assertEqual(job.snapshot()["summary"]["environments"][0]["verdict"], "CANCELLED")

    def test_uploaded_files_are_opaque_bounded_local_copies(self):
        data = self.plugin.read_bytes()
        imported = self.app.import_file(io.BytesIO(data), len(data), "safe.jar", "plugin")
        request = self.request()
        request["plugin"] = {"file_id": imported["file_id"]}
        generated = self.app.generate_configuration(request)
        self.assertEqual(Path(generated["plugin"]).read_bytes(), data)
        self.assertTrue(Path(generated["plugin"]).is_relative_to(self.app.upload_root))
        for name in ("../evil.jar", "evil%2Fname.jar", "evil.txt", "%00evil.jar"):
            with self.subTest(name=name), self.assertRaises(WebError):
                self.app.import_file(io.BytesIO(b"x"), 1, name, "plugin")

    def test_artifact_access_is_exact_and_rejects_file_replacement(self):
        path = self.root / "result.json"
        path.write_text("{}", encoding="utf-8")
        artifacts = self.app._register_artifacts([("report", path)])
        registered = next(iter(artifacts.values()))
        from pluginmatrix.control import RunControl
        from pluginmatrix.web import Job
        saved = Job("a" * 32, "single", 1, RunControl(), {})
        saved.status = "completed"
        saved.artifacts = artifacts
        with self.app._lock:
            self.app._jobs[saved.id] = saved
        artifact, stream = self.app.artifact(saved.id, registered.id)
        self.assertEqual(stream.read(), b"{}")
        stream.close()
        replacement = self.root / "replacement.json"
        replacement.write_text('{"changed":true}', encoding="utf-8")
        os.replace(replacement, path)
        with self.assertRaisesRegex(WebError, "changed"):
            self.app.artifact(saved.id, registered.id)
        with self.assertRaises(WebError):
            self.app.artifact(saved.id, "b" * 32)


class WebHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.server = LocalWebServer(("127.0.0.1", 0), WebApplication(root / "state", root / "cache"))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server.app.close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def connection(self):
        return http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)

    def session(self):
        connection = self.connection()
        connection.request("GET", "/", headers={"Host": f"127.0.0.1:{self.port}"})
        response = connection.getresponse()
        body = response.read().decode("utf-8")
        cookie = response.getheader("Set-Cookie").split(";", 1)[0]
        token = re.search(r'name="pluginmatrix-token" content="([a-f0-9]+)"', body).group(1)
        connection.close()
        return cookie, token, body

    def test_loopback_page_has_strict_headers_and_provider_api(self):
        cookie, _, body = self.session()
        self.assertIn("same narrow meaning as the CLI", body)
        self.assertIn("Folia PASS", body)
        connection = self.connection()
        connection.request("GET", "/assets/app.js", headers={"Host": f"127.0.0.1:{self.port}"})
        script_response = connection.getresponse()
        script = script_response.read().decode("utf-8")
        self.assertEqual(script_response.status, 200)
        self.assertIn("textContent", script)
        self.assertNotIn("innerHTML", script)
        connection.close()
        connection = self.connection()
        connection.request("GET", "/api/providers", headers={"Host": f"127.0.0.1:{self.port}", "Cookie": cookie})
        response = connection.getresponse()
        providers = json.loads(response.read())
        self.assertEqual(response.status, 200)
        self.assertIn("default-src 'none'", response.getheader("Content-Security-Policy"))
        self.assertEqual([item["type"] for item in providers["providers"]], ["paper", "purpur", "folia", "local"])
        connection.close()

    def test_host_cookie_origin_token_and_request_injection_are_rejected(self):
        cookie, token, _ = self.session()
        connection = self.connection()
        connection.request("GET", "/api/jobs", headers={"Host": "attacker.example"})
        response = connection.getresponse()
        response.read()
        self.assertEqual(response.status, 400)
        connection.close()
        body = json.dumps({"path": "<script>alert(1)</script>"})
        connection = self.connection()
        connection.request("POST", "/api/config/import", body=body, headers={
            "Host": f"127.0.0.1:{self.port}", "Cookie": cookie, "Content-Type": "application/json",
            "X-PluginMatrix-Token": token, "Origin": "http://attacker.example",
        })
        response = connection.getresponse()
        payload = response.read()
        self.assertEqual(response.status, 403)
        self.assertEqual(response.getheader("Content-Type"), "application/json; charset=utf-8")
        self.assertNotIn(b"<script>", payload)
        connection.close()
        reflected = json.dumps({"<script>": True})
        connection = self.connection()
        connection.request("POST", "/api/jobs", body=reflected, headers={
            "Host": f"127.0.0.1:{self.port}", "Cookie": cookie, "Content-Type": "application/json",
            "X-PluginMatrix-Token": token, "Origin": f"http://127.0.0.1:{self.port}",
        })
        response = connection.getresponse()
        payload = response.read()
        self.assertEqual(response.status, 400)
        self.assertNotIn(b"<script>", payload)
        self.assertIn(b"\\u003cscript\\u003e", payload)
        connection.close()


if __name__ == "__main__":
    unittest.main()
