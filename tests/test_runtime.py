import json
import subprocess
import sys
import textwrap
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from probe_support import probe_writer

from pluginmatrix.runtime import (
    RuntimeEvidence,
    _allocate_server_port,
    _create_run_dir,
    _stop_process,
    _write_server_properties,
    run_server_process,
)


class RuntimeEvidenceTests(unittest.TestCase):
    def test_environment_failure_wins_over_start_timeout(self):
        evidence = RuntimeEvidence("Example", "example.jar")
        evidence.observe_line("Failed to download mojang_1.20.1.jar", 0.1)
        evidence.observe_line("java.net.SocketException: Connection reset", 0.2)
        evidence.finalize(0.3, process_alive=True, timed_out=True)
        self.assertEqual(
            evidence.verdict(process_alive=True, timed_out=True),
            ("ENVIRONMENT_INVALID", "environment", "java.net.SocketException: Connection reset"),
        )
        self.assertTrue(any(event.kind == "environment_failure" for event in evidence.events))

    def test_nonfatal_auth_network_error_does_not_mask_plugin_load_failure(self):
        evidence = RuntimeEvidence("Example", "example.jar")
        evidence.observe_line("Failed to request yggdrasil public key", 0.1)
        evidence.observe_line("java.net.SocketException: Connection reset", 0.2)
        evidence.observe_line("UnknownDependencyException: Unknown dependency Vault for Example", 0.3)
        evidence.observe_line('[Server thread/INFO]: Done (1.0s)! For help, type "help"', 0.4)
        self.assertEqual(
            evidence.verdict(process_alive=True, timed_out=False)[0],
            "PLUGIN_LOAD_FAILED",
        )

    def test_plugin_enable_failure_is_not_pass(self):
        evidence = RuntimeEvidence("Example", "example.jar")
        evidence.observe_line("[Server thread/INFO]: Enabling Example v1.0", 0.1)
        evidence.observe_line("[Server thread/ERROR]: Error occurred while enabling Example v1.0", 0.2)
        evidence.observe_line("[Server thread/INFO]: Done (1.0s)! For help, type \"help\"", 0.3)
        self.assertEqual(
            evidence.verdict(process_alive=True, timed_out=False),
            ("PLUGIN_ENABLE_FAILED", "plugin_enable", "[Server thread/ERROR]: Error occurred while enabling Example v1.0"),
        )

    def test_direct_runtime_probe_confirms_enabled_plugin(self):
        evidence = RuntimeEvidence("Example", "example.jar", require_direct_runtime=True)
        evidence.observe_line("[Server thread/INFO]: Done (1.0s)! For help, type \"help\"", 0.1)
        evidence.observe_probe(
            {
                "probe": "pluginmatrix",
                "target_present": True,
                "target_name": "Example",
                "target_version": "1.0",
                "target_enabled": True,
            },
            0.2,
        )
        self.assertEqual(evidence.verdict(process_alive=True, timed_out=False)[0], "UNKNOWN_FAILURE")
        evidence.observation_complete = True
        self.assertEqual(evidence.verdict(process_alive=True, timed_out=False)[0], "PASS")

    def test_required_probe_missing_is_not_pass(self):
        evidence = RuntimeEvidence("Example", require_direct_runtime=True)
        evidence.observe_line('[Server thread/INFO]: Enabling Example v1.0', 0.1)
        evidence.observe_line('[Server thread/INFO]: Done (1.0s)! For help, type "help"', 0.2)
        self.assertEqual(evidence.verdict(process_alive=True, timed_out=False)[0], "UNKNOWN_FAILURE")

    def test_direct_probe_detects_present_but_disabled_plugin(self):
        evidence = RuntimeEvidence("Example", require_direct_runtime=True)
        evidence.observe_probe(
            {
                "probe": "pluginmatrix",
                "target_present": True,
                "target_name": "Example",
                "target_version": "1.0",
                "target_enabled": False,
            },
            0.2,
        )
        self.assertEqual(evidence.verdict(process_alive=True, timed_out=False)[0], "PLUGIN_DISABLED")


class RuntimeProcessTests(unittest.TestCase):
    def run_script(
        self,
        lines: list[str],
        sleep_after: float = 1.0,
        timeout: float = 1.0,
        stability: float = 0.1,
        exit_code: int = 0,
        probe_payload: dict | None = None,
    ):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "fake_server.py"
            script.write_text(
                "import sys, time\n"
                + "".join(f"print({line!r}, flush=True)\n" for line in lines)
                + (
                    probe_writer('pluginmatrix-runtime-evidence.json', **probe_payload)
                    if probe_payload
                    else ""
                )
                + f"time.sleep({sleep_after!r})\n"
                + f"raise SystemExit({exit_code})\n",
                encoding="utf-8",
            )
            result = run_server_process(
                command=[sys.executable, str(script)],
                server_dir=root,
                log_path=root / "server.log",
                plugin_name="Example",
                plugin_jar_name="example.jar",
                timeout=timeout,
                stability=stability,
                probe_path=root / "pluginmatrix-runtime-evidence.json" if probe_payload else None,
                require_direct_runtime=bool(probe_payload),
            )
            return result, (root / "server.log").read_text(encoding="utf-8")

    def test_normal_start_and_enable_pass(self):
        result, log = self.run_script(
            ["[Server thread/INFO]: Enabling Example v1.0", '[Server thread/INFO]: Done (1.0s)! For help, type "help"'],
            probe_payload={'target_name': 'Example'},
        )
        self.assertEqual(result.evidence.verdict(result.exit_code is None, result.timed_out)[0], "PASS")
        self.assertTrue(any(event.kind == "server_process_started" for event in result.evidence.events))
        self.assertTrue(any(event.kind == "server_ready" for event in result.evidence.events))
        self.assertIn("Enabling Example", log)

    def test_process_collects_direct_probe_evidence(self):
        result, _ = self.run_script(
            ['[Server thread/INFO]: Done (1.0s)! For help, type "help"'],
            stability=0.5,
            probe_payload={
                "probe": "pluginmatrix",
                "target_present": True,
                "target_name": "Example",
                "target_version": "1.0",
                "target_enabled": True,
            },
        )
        self.assertTrue(result.evidence.direct_runtime_observed)
        self.assertTrue(result.evidence.direct_plugin_enabled)
        self.assertEqual(result.evidence.verdict(result.exit_code is None, result.timed_out)[0], "PASS")

    def test_plugin_not_discovered(self):
        result, _ = self.run_script(['[Server thread/INFO]: Done (1.0s)! For help, type "help"'])
        self.assertEqual(result.evidence.verdict(result.exit_code is None, result.timed_out)[0], "PLUGIN_NOT_DISCOVERED")

    def test_dependency_missing_is_load_failure(self):
        result, _ = self.run_script(
            ["[Server thread/ERROR]: UnknownDependencyException: Unknown dependency Vault for Example", '[Server thread/INFO]: Done (1.0s)! For help, type "help"']
        )
        self.assertEqual(result.evidence.verdict(result.exit_code is None, result.timed_out)[0], "PLUGIN_LOAD_FAILED")

    def test_load_failure(self):
        result, _ = self.run_script(
            ["[Server thread/ERROR]: Could not load plugin Example: InvalidPluginException", '[Server thread/INFO]: Done (1.0s)! For help, type "help"']
        )
        self.assertEqual(result.evidence.verdict(result.exit_code is None, result.timed_out)[0], "PLUGIN_LOAD_FAILED")

    def test_on_enable_exception(self):
        result, _ = self.run_script(
            ["[Server thread/INFO]: Enabling Example v1.0", "[Server thread/ERROR]: Error occurred while enabling Example v1.0", '[Server thread/INFO]: Done (1.0s)! For help, type "help"']
        )
        self.assertEqual(result.evidence.verdict(result.exit_code is None, result.timed_out)[0], "PLUGIN_ENABLE_FAILED")

    def test_plugin_disabled_after_ready(self):
        result, _ = self.run_script(
            ["[Server thread/INFO]: Enabling Example v1.0", '[Server thread/INFO]: Done (1.0s)! For help, type "help"', "[Server thread/INFO]: Disabling Example v1.0"]
        )
        self.assertEqual(result.evidence.verdict(result.exit_code is None, result.timed_out)[0], "PLUGIN_DISABLED")

    def test_server_start_failure(self):
        result, _ = self.run_script(["[Server thread/ERROR]: Error during server startup: failed to bind to port"], sleep_after=0, exit_code=1)
        self.assertEqual(result.evidence.verdict(result.exit_code is None, result.timed_out)[0], "SERVER_START_FAILED")

    def test_startup_timeout(self):
        result, _ = self.run_script([], sleep_after=1.0, timeout=0.15)
        self.assertEqual(result.evidence.verdict(result.exit_code is None, result.timed_out)[0], "SERVER_START_TIMEOUT")
        self.assertTrue(any(event.kind == "startup_timeout" for event in result.evidence.events))

    def test_network_failure_is_environment_invalid(self):
        result, _ = self.run_script(
            ["Failed to download mojang_1.20.1.jar", "java.net.SocketException: Connection reset"],
            sleep_after=0,
            exit_code=1,
        )
        self.assertEqual(result.evidence.verdict(result.exit_code is None, result.timed_out)[0], "ENVIRONMENT_INVALID")

    def test_server_shutdown_during_window_is_not_misclassified_as_plugin_disabled(self):
        evidence = RuntimeEvidence('Example')
        evidence.server_ready = True
        evidence.plugin_discovered = True
        evidence.plugin_enable_started = True
        evidence.direct_runtime_observed = True
        evidence.direct_plugin_enabled = True
        evidence.observe_line('Stopping server', 1)
        evidence.observe_line('[Example] Disabling Example v1.0', 1.1)
        self.assertEqual(evidence.verdict(False, False)[0], 'SERVER_START_FAILED')

    def test_server_properties_use_isolated_port(self):
        with TemporaryDirectory() as temp:
            path = _write_server_properties(Path(temp), 28123)
            properties = path.read_text(encoding="utf-8")
            self.assertIn("server-port=28123", properties)
            self.assertIn("server-ip=127.0.0.1", properties)
            self.assertIn("online-mode=false", properties)
            self.assertIn("level-seed=pluginmatrix", properties)

    def test_port_allocator_returns_bindable_local_port(self):
        port = _allocate_server_port()
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", port))

    def test_run_directories_are_unique(self):
        with TemporaryDirectory() as temp:
            first = _create_run_dir(Path(temp))
            second = _create_run_dir(Path(temp))
            self.assertNotEqual(first, second)
            self.assertTrue(first.is_dir())
            self.assertTrue(second.is_dir())

    def test_process_stop_terminates_child(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        try:
            _stop_process(process)
            self.assertIsNotNone(process.poll())
        finally:
            if process.poll() is None:
                process.kill()
