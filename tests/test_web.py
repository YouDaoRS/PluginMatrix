import http.client
import io
import json
import os
import re
import socket
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

    def test_artifact_rejects_same_size_edit_and_links(self):
        from pluginmatrix.control import RunControl
        from pluginmatrix.web import Job
        path = self.root / "result.json"
        path.write_bytes(b"original")
        job = Job("c" * 32, "single", 1, RunControl(), {})
        job.artifacts = self.app._register_artifacts([("report", path)])
        self.app._jobs[job.id] = job
        artifact_id = next(iter(job.artifacts))
        path.write_bytes(b"modified")
        os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1000000000))
        with self.assertRaises(WebError):
            self.app.artifact(job.id, artifact_id)
        alias = self.root / "alias.json"
        os.link(path, alias)
        self.assertEqual(self.app._register_artifacts([("report", alias)]), {})

    def test_artifact_registration_rejects_symlink_before_resolving(self):
        path = self.root / "secret.json"
        path.write_bytes(b"secret")
        alias = self.root / "alias.json"
        try:
            alias.symlink_to(path)
        except OSError:
            self.skipTest("symlink creation unavailable")
        self.assertEqual(self.app._register_artifacts([("report", alias)]), {})

    def test_upload_does_not_hold_job_lock_and_reserves_total_quota(self):
        entered, release = threading.Event(), threading.Event()
        errors = []
        class SlowStream:
            def read(self, size):
                entered.set()
                release.wait(3)
                return b"x"
        def upload():
            try:
                self.app.import_file(SlowStream(), 1, "a.jar", "plugin")
            except Exception as exc:
                errors.append(exc)
        worker = threading.Thread(target=upload)
        worker.start()
        try:
            self.assertTrue(entered.wait(1))
            acquired = self.app._lock.acquire(timeout=.2)
            if acquired:
                self.app._lock.release()
            self.assertTrue(acquired, "network read held the global job lock")
            with patch("pluginmatrix.web.MAX_UPLOAD_BYTES", 1), self.assertRaises(WebError):
                self.app.import_file(io.BytesIO(b"x"), 1, "b.jar", "plugin")
        finally:
            release.set()
            worker.join(5)
        self.assertEqual(errors, [])

    def test_config_reads_bounded_open_descriptor_even_when_path_changes(self):
        source = self.root / "matrix.json"
        application.init_configuration(source, plugin=self.plugin, servers=[ServerSpec("paper", "1.20.1")], java="17")
        from pluginmatrix.web import _open_regular
        opened = _open_regular(source)
        try:
            with patch("pluginmatrix.web._open_regular", return_value=opened), patch.object(Path, "read_text", side_effect=AssertionError("reopened config")):
                self.assertEqual(self.app.import_configuration(str(source))["configuration"]["environments"][0]["java"], "17")
        finally:
            opened.close()


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

    def raw(self, request):
        with socket.create_connection(("127.0.0.1", self.port), timeout=2) as connection:
            connection.sendall(request.encode("ascii"))
            chunks = []
            while True:
                try:
                    data = connection.recv(65536)
                except ConnectionError:
                    return b"".join(chunks)
                if not data:
                    return b"".join(chunks)
                chunks.append(data)

    def test_ambiguous_framing_and_pipeline_are_closed(self):
        host = f"Host: 127.0.0.1:{self.port}\r\n"
        for headers in (host + "Host: attacker\r\n", host + "Content-Length: 0\r\nContent-Length: 1\r\n",
                        host + "Transfer-Encoding: chunked\r\n", host + "Content-Length: 1\r\n",
                        host + "Origin: http://attacker\r\n"):
            with self.subTest(headers=headers):
                response = self.raw("GET /health HTTP/1.1\r\n" + headers + "\r\nGET /health HTTP/1.1\r\n" + host + "\r\n")
                self.assertEqual(response.count(b"HTTP/1.1"), 1)
                self.assertNotIn(b"200 OK", response)
        response = self.raw("GET /health HTTP/1.1\r\n" + host + "\r\nGET /health HTTP/1.1\r\n" + host + "\r\n")
        self.assertEqual(response.count(b"200 OK"), 1)

    def test_absolute_connection_deadline_and_shutdown_interrupt_partial_headers(self):
        with patch("pluginmatrix.web.REQUEST_SECONDS", .2):
            with socket.create_connection(("127.0.0.1", self.port), timeout=2) as connection:
                connection.sendall(b"GET / HTTP/1.1\r\nHost:")
                time.sleep(.3)
                self.assertEqual(connection.recv(1024), b"")
        with socket.create_connection(("127.0.0.1", self.port), timeout=2) as connection:
            connection.sendall(b"GET / HTTP/1.1\r\nHost:")
            self.server.shutdown()
            closer = threading.Thread(target=self.server.server_close)
            closer.start()
            closer.join(2)
            self.assertFalse(closer.is_alive(), "server close waited for an incomplete HTTP request")

    def test_connection_workers_are_bounded(self):
        # Occupy the capacity without allocating worker threads, then verify rejection.
        from pluginmatrix.web import MAX_HTTP_CONNECTIONS
        for _ in range(MAX_HTTP_CONNECTIONS):
            self.assertTrue(self.server._connection_slots.acquire(False))
        try:
            self.assertEqual(self.raw(f"GET /health HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n\r\n"), b"")
        finally:
            for _ in range(MAX_HTTP_CONNECTIONS):
                self.server._connection_slots.release()

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
