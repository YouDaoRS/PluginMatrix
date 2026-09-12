import json
import tempfile
import unittest
from pathlib import Path

from pluginmatrix.cli import main
from pluginmatrix.matrix import MatrixConfigError, load_matrix_config, matrix_exit_code, run_matrix
from pluginmatrix.model import EvidenceEvent, VerificationResult


class MatrixTests(unittest.TestCase):
    def make_config(self, root: Path, environments=None, options=None) -> Path:
        plugin = root / "Example.jar"
        plugin.write_bytes(b"fixture")
        config = {
            "plugin": "Example.jar",
            "environments": environments
            or [
                {"paper": "1.19.4", "java": 17, "paper_build": 550},
                {"paper": "1.20.1", "java": 17},
                {"paper": "1.20.4", "java": 17, "paper_build": 499},
            ],
        }
        if options:
            config["options"] = options
        path = root / "matrix.json"
        path.write_text(json.dumps(config), encoding="utf-8")
        return path

    def fake_verifier(self, calls, failures=None):
        failures = failures or {}

        def verify(**kwargs):
            calls.append(kwargs)
            environment = (kwargs["paper_version"], kwargs["java"])
            result = VerificationResult(
                result=failures.get(environment, "PASS"),
                metadata={
                    "plugin_name": "Example",
                    "plugin_version": "1.0.0",
                    "minecraft_version": kwargs["paper_version"],
                    "paper_build": kwargs.get("paper_build") or 999,
                    "java_runtime_version": f"{kwargs['java']}.0.0",
                },
                workdir=str(kwargs["work_root"] / f"fake-{len(calls)}"),
                log_path=str(kwargs["work_root"] / f"fake-{len(calls)}" / "server.log"),
                evidence=[EvidenceEvent("server_ready", 0.1, detail="fixture")],
            )
            if result.result != "PASS":
                result.failure_stage = "plugin_load"
                result.reason = "fixture failure"
            Path(result.workdir).mkdir(parents=True)
            Path(result.log_path).write_text("fixture\n", encoding="utf-8")
            return result

        return verify

    def test_all_environments_pass_and_report_links_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.make_config(root, options={"report": "matrix-report.json"})
            config = load_matrix_config(path)
            calls = []
            report = run_matrix(config, verifier=self.fake_verifier(calls))
            self.assertEqual(len(calls), 3)
            self.assertEqual(report["summary"], {"total": 3, "passed": 3, "failed": 0})
            self.assertTrue(config.report_path.is_file())
            payload = json.loads(config.report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["plugin"]["plugin_name"], "Example")
            self.assertEqual(len(payload["environments"]), 3)
            for entry in payload["environments"]:
                self.assertTrue(Path(entry["runtime_report"]).is_file())
                self.assertTrue(Path(entry["artifacts"]["server_log"]).is_file())
            self.assertEqual(matrix_exit_code(report), 0)

    def test_middle_failure_does_not_stop_following_environment(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.make_config(
                root,
                environments=[
                    {"paper": "1.19.4", "java": 17},
                    {"paper": "1.20.1", "java": 17},
                    {"paper": "1.20.4", "java": 17},
                ],
            )
            calls = []
            verifier = self.fake_verifier(calls, {("1.20.1", "17"): "PLUGIN_LOAD_FAILED"})
            report = run_matrix(load_matrix_config(path), verifier=verifier)
            self.assertEqual(len(calls), 3)
            self.assertEqual(report["summary"], {"total": 3, "passed": 2, "failed": 1})
            self.assertEqual(matrix_exit_code(report), 1)

    def test_invalid_config_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.make_config(
                root,
                environments=[
                    {"paper": "1.20.1", "java": 17},
                    {"paper": "1.20.1", "java": 17},
                ],
            )
            with self.assertRaises(MatrixConfigError):
                load_matrix_config(path)

    def test_fixed_build_is_forwarded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.make_config(root, environments=[{"paper": "1.20.1", "java": 17, "paper_build": 196}])
            calls = []
            run_matrix(load_matrix_config(path), verifier=self.fake_verifier(calls))
            self.assertEqual(calls[0]["paper_build"], 196)

    def test_unexpected_environment_error_is_recorded_and_returns_internal_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.make_config(root, environments=[
                {"paper": "1.20.1", "java": 17},
                {"paper": "1.20.4", "java": 17},
            ])
            calls = []

            def verifier(**kwargs):
                calls.append(kwargs)
                if len(calls) == 1:
                    raise RuntimeError("fixture verifier crash")
                return self.fake_verifier([])(**kwargs)

            report = run_matrix(load_matrix_config(path), verifier=verifier)
            self.assertEqual(len(calls), 2)
            self.assertEqual(report["internal_errors"], 1)
            self.assertEqual(matrix_exit_code(report), 3)

    def test_cli_configuration_error_exit_code_and_single_env_compatibility(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            missing = root / "missing.json"
            self.assertEqual(main(["matrix", str(missing)]), 2)
            with self.assertRaises(SystemExit) as exit_info:
                main(["test", "--help"])
            self.assertEqual(exit_info.exception.code, 0)
