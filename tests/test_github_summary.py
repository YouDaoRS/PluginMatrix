import json
import tempfile
import unittest
from pathlib import Path

from pluginmatrix.github_summary import main, render_job_summary


class GitHubSummaryTests(unittest.TestCase):
    def test_success_report_uses_report_verdict_and_artifact_references(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / "matrix-report.json"
            report.write_text(
                json.dumps(
                    {
                        "plugin": {"plugin_name": "Example"},
                        "environments": [
                            {
                                "id": "paper-1.20.1-java-17-build-196",
                                "verdict": "PASS",
                                "failure_stage": None,
                                "primary_evidence": ".pluginmatrix/runs/run-1/server.log",
                                "artifacts": {"server_log": ".pluginmatrix/runs/run-1/server.log"},
                            }
                        ],
                        "summary": {"total": 1, "passed": 1, "failed": 0},
                    }
                ),
                encoding="utf-8",
            )
            summary = render_job_summary(report)
            self.assertIn("`PASS`", summary)
            self.assertIn("1 passed, 0 failed of 1", summary)
            self.assertIn("server.log", summary)
            self.assertIn("pluginmatrix-matrix-report", summary)

    def test_failure_report_shows_verdict_stage_reason_and_primary_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "matrix-report.json"
            report.write_text(
                json.dumps(
                    {
                        "plugin": {"plugin_jar": "Example.jar"},
                        "environments": [
                            {
                                "id": "env-1",
                                "verdict": "PLUGIN_LOAD_FAILED",
                                "failure_stage": "plugin_load",
                                "reason": "missing dependency",
                                "primary_evidence": "runs/env-1/server.log",
                                "artifacts": {},
                            }
                        ],
                        "summary": {"total": 1, "passed": 0, "failed": 1},
                    }
                ),
                encoding="utf-8",
            )
            summary = render_job_summary(report)
            self.assertIn("### Failures", summary)
            self.assertIn("`PLUGIN_LOAD_FAILED`", summary)
            self.assertIn("`plugin_load`", summary)
            self.assertIn("missing dependency", summary)
            self.assertIn("runs/env-1/server.log", summary)

    def test_missing_corrupt_and_non_object_reports_are_tolerated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            missing = render_job_summary(root / "missing.json")
            self.assertIn("was not generated", missing)

            corrupt_path = root / "corrupt.json"
            corrupt_path.write_text("{broken", encoding="utf-8")
            self.assertIn("could not be read as valid JSON", render_job_summary(corrupt_path))

            list_path = root / "list.json"
            list_path.write_text("[]", encoding="utf-8")
            self.assertIn("unexpected format", render_job_summary(list_path))

    def test_module_appends_to_summary_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / "missing.json"
            summary = root / "summary.md"
            summary.write_text("existing\n", encoding="utf-8")
            self.assertEqual(main([str(report), str(summary)]), 0)
            self.assertTrue(summary.read_text(encoding="utf-8").startswith("existing\n## PluginMatrix"))
