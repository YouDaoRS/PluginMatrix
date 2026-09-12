import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from pluginmatrix.cli import _print_matrix_result, main
from pluginmatrix.matrix import (
    MatrixConfigError,
    load_matrix_config,
    matrix_exit_code,
    run_matrix,
    validate_matrix_preconditions,
)
from pluginmatrix.model import EvidenceEvent, VerificationResult
from tests.test_preflight import make_plugin


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
            self.assertEqual(payload["config_source"], str(config.source_path))
            self.assertEqual(len(payload["environments"]), 3)
            for entry in payload["environments"]:
                self.assertTrue(Path(entry["runtime_report"]).is_file())
                self.assertTrue(Path(entry["artifacts"]["server_log"]).is_file())
                self.assertEqual(entry["primary_evidence"], entry["artifacts"]["server_log"])
                self.assertEqual(
                    entry["artifact_availability"],
                    {"run_dir": True, "server_log": True, "runtime_report": True},
                )
            self.assertEqual(payload["artifacts"]["matrix_report"], str(config.report_path))
            self.assertEqual(payload["artifacts"]["runtime_root"], str(config.work_dir))
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

    def test_failure_before_server_launch_points_to_runtime_report_and_marks_log_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = load_matrix_config(
                self.make_config(root, environments=[{"paper": "1.20.1", "java": 17}])
            )

            def verifier(**kwargs):
                workdir = kwargs["work_root"] / "early-failure"
                workdir.mkdir(parents=True)
                return VerificationResult(
                    result="ENVIRONMENT_INVALID",
                    failure_stage="environment",
                    reason="fixture Java failure",
                    metadata={"requested_paper": "1.20.1", "requested_java": "17"},
                    workdir=str(workdir),
                    log_path=str(workdir / "server.log"),
                )

            report = run_matrix(config, verifier=verifier)
            entry = report["environments"][0]
            self.assertEqual(entry["primary_evidence"], entry["artifacts"]["runtime_report"])
            self.assertTrue(entry["artifact_availability"]["runtime_report"])
            self.assertFalse(entry["artifact_availability"]["server_log"])

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
            with self.assertRaisesRegex(MatrixConfigError, "conflicts with an earlier environment"):
                load_matrix_config(path)

    def test_config_errors_name_field_value_expectation_and_fix(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.make_config(root, environments=[])
            document = json.loads(path.read_text(encoding="utf-8"))
            document["environments"] = []
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(MatrixConfigError) as captured:
                load_matrix_config(path)
            message = str(captured.exception)
            self.assertIn("field 'environments'", message)
            self.assertIn("expected a non-empty array", message)
            self.assertIn("Fix:", message)

    def test_missing_plugin_explains_config_relative_path_and_hosted_input(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.make_config(root)
            document = json.loads(path.read_text(encoding="utf-8"))
            document["plugin"] = "missing/Example.jar"
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(MatrixConfigError) as captured:
                load_matrix_config(path)
            message = str(captured.exception)
            self.assertIn("field 'plugin'", message)
            self.assertIn(str(root), message)
            self.assertIn("plugin_jar inputs", message)

    def test_preflight_rejects_invalid_plugin_and_unavailable_java_together(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.make_config(root, environments=[{"paper": "1.20.1", "java": 17}])
            config = load_matrix_config(path)

            def missing_java(_value):
                raise ValueError("fixture Java missing")

            with self.assertRaises(MatrixConfigError) as captured:
                validate_matrix_preconditions(
                    config,
                    java_resolver=missing_java,
                    javac_resolver=lambda _: "javac",
                )
            message = str(captured.exception)
            self.assertIn("plugin JAR failed preflight", message)
            self.assertIn("fixture Java missing", message)
            self.assertIn("does not download JDKs", message)

    def test_preflight_rejects_uncreatable_output_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            blocked = root / "blocked"
            blocked.write_text("not a directory", encoding="utf-8")
            path = self.make_config(root, options={"work_dir": "blocked/child"})
            make_plugin(root / "Example.jar", "name: Example\nversion: 1.0\nmain: example.Main\napi-version: '1.20'\n")
            with self.assertRaises(MatrixConfigError) as captured:
                validate_matrix_preconditions(
                    load_matrix_config(path),
                    java_resolver=lambda _: ("java", "17.0.1"),
                    javac_resolver=lambda _: "javac",
                )
            message = str(captured.exception)
            self.assertIn("options.work_dir", message)
            self.assertIn("not writable", message)
            self.assertIn("Fix:", message)

    def test_preflight_rejects_report_parent_that_is_a_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            blocked = root / "blocked-report-parent"
            blocked.write_text("not a directory", encoding="utf-8")
            path = self.make_config(root, options={"report": "blocked-report-parent/report.json"})
            make_plugin(root / "Example.jar", "name: Example\nversion: 1.0\nmain: example.Main\napi-version: '1.20'\n")
            with self.assertRaises(MatrixConfigError) as captured:
                validate_matrix_preconditions(
                    load_matrix_config(path),
                    java_resolver=lambda _: ("java", "17.0.1"),
                    javac_resolver=lambda _: "javac",
                )
            self.assertIn("options.report parent", str(captured.exception))

    def test_preflight_rejects_conflicting_work_and_cache_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.make_config(root, options={"work_dir": "output", "cache_dir": "output"})
            make_plugin(root / "Example.jar", "name: Example\nversion: 1.0\nmain: example.Main\napi-version: '1.20'\n")
            with self.assertRaisesRegex(MatrixConfigError, "separate run and download-cache directories"):
                validate_matrix_preconditions(
                    load_matrix_config(path),
                    java_resolver=lambda _: ("java", "17.0.1"),
                    javac_resolver=lambda _: "javac",
                )

    def test_preflight_accepts_valid_plugin_paths_and_java(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.make_config(root, environments=[{"paper": "1.20.1", "java": 17}])
            make_plugin(root / "Example.jar", "name: Example\nversion: 1.0\nmain: example.Main\napi-version: '1.20'\n")
            config = load_matrix_config(path)
            preflight = validate_matrix_preconditions(
                config,
                java_resolver=lambda _: ("java", "17.0.1"),
                javac_resolver=lambda _: "javac",
            )
            self.assertEqual(preflight["plugin"]["plugin_name"], "Example")
            self.assertEqual(preflight["java_runtimes"]["17"]["runtime_version"], "17.0.1")

    def test_preflight_requires_full_jdk_with_javac(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self.make_config(root, environments=[{"paper": "1.20.1", "java": 17}])
            make_plugin(root / "Example.jar", "name: Example\nversion: 1.0\nmain: example.Main\napi-version: '1.20'\n")
            with self.assertRaisesRegex(MatrixConfigError, "full JDK"):
                validate_matrix_preconditions(
                    load_matrix_config(path),
                    java_resolver=lambda _: ("java", "17.0.1"),
                    javac_resolver=lambda _: None,
                )

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

    def test_single_environment_cli_still_writes_report_and_returns_verdict_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plugin = root / "Example.jar"
            plugin.write_bytes(b"fixture")
            workdir = root / "runs" / "run-1"
            workdir.mkdir(parents=True)
            result = VerificationResult(
                result="PLUGIN_NOT_DISCOVERED",
                failure_stage="plugin_discovery",
                reason="fixture failure",
                metadata={"requested_paper": "1.20.1", "requested_java": "17"},
                workdir=str(workdir),
                log_path=str(workdir / "server.log"),
            )
            custom_report = root / "reports" / "single-result.json"
            with patch("pluginmatrix.cli.verify", return_value=result):
                exit_code = main(
                    [
                        "test",
                        "--plugin",
                        str(plugin),
                        "--paper",
                        "1.20.1",
                        "--java",
                        "17",
                        "--work-dir",
                        str(root / "runs"),
                        "--cache-dir",
                        str(root / "cache"),
                        "--report",
                        str(custom_report),
                    ]
                )
            self.assertEqual(exit_code, 1)
            self.assertTrue(custom_report.is_file())

    def test_cli_failure_summary_prioritizes_stage_and_evidence_and_ends_with_report(self):
        report = {
            "environments": [
                {
                    "id": "paper-1.20.1-java-17-build-196",
                    "verdict": "PLUGIN_ENABLE_FAILED",
                    "failure_stage": "plugin_enable",
                    "reason": "fixture enable error",
                    "primary_evidence": "runs/run-1/server.log",
                    "artifacts": {
                        "runtime_report": "runs/run-1/result.json",
                        "server_log": "runs/run-1/server.log",
                        "run_dir": "runs/run-1",
                    },
                }
            ],
            "summary": {"total": 1, "passed": 0, "failed": 1},
        }
        output = StringIO()
        with redirect_stdout(output):
            _print_matrix_result(report, Path("matrix-report.json"))
        rendered = output.getvalue()
        self.assertIn("Failure stage: plugin_enable", rendered)
        self.assertIn("Primary evidence: runs/run-1/server.log", rendered)
        self.assertTrue(rendered.rstrip().endswith("Matrix report: matrix-report.json"))
