import unittest
from pathlib import Path
from textwrap import dedent


ROOT = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def read(self, name: str) -> str:
        return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")

    def test_offline_ci_has_only_push_pr_and_no_matrix_invocation(self):
        workflow = self.read("ci.yml")
        self.assertIn("push:", workflow)
        self.assertIn("pull_request:", workflow)
        self.assertIn("python -m unittest discover -s tests -v", workflow)
        self.assertIn("python -m compileall pluginmatrix tests", workflow)
        self.assertNotIn("pluginmatrix matrix", workflow)
        self.assertNotIn("paper.jar", workflow)

    def test_manual_matrix_workflow_uses_dispatch_and_existing_cli(self):
        workflow = self.read("matrix.yml")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertNotIn("\n  pull_request:", workflow)
        self.assertIn("config:", workflow)
        self.assertIn("plugin_jar:", workflow)
        self.assertIn('java-version: "17"', workflow)
        self.assertIn("id: prepare", workflow)
        self.assertIn("echo \"exit_code=2\"", workflow)
        self.assertIn("must be a repository-relative path", workflow)
        self.assertIn('cp -- "$PLUGIN_JAR" .ci/plugin.jar', workflow)
        self.assertIn('document["plugin"] = "plugin.jar"', workflow)
        self.assertIn('options["work_dir"] = "../.pluginmatrix/runs"', workflow)
        self.assertIn('options["report"] = "../.pluginmatrix/matrix-report.json"', workflow)
        self.assertIn("if: steps.prepare.outputs.exit_code == '0'", workflow)
        self.assertIn("python -m pluginmatrix matrix .ci/matrix.json", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("pluginmatrix-matrix-report", workflow)
        self.assertIn("pluginmatrix-runtime-artifacts", workflow)
        self.assertIn("GITHUB_STEP_SUMMARY", workflow)
        self.assertIn("json.JSONDecodeError", workflow)
        self.assertIn("unexpected format", workflow)
        self.assertIn("if: always()", workflow)
        self.assertNotIn("pull_request_target", workflow)

    def test_manual_example_is_valid_json_and_java_17(self):
        import json

        config = json.loads((ROOT / "examples" / "ci-matrix.json").read_text(encoding="utf-8"))
        self.assertTrue(config["environments"])
        self.assertTrue(all(str(item["java"]) == "17" for item in config["environments"]))

    def test_manual_matrix_job_summary_python_is_valid(self):
        workflow = self.read("matrix.yml")
        marker = "          python - <<'PY'\n"
        scripts = workflow.split(marker)[1:]
        self.assertGreaterEqual(len(scripts), 2)
        summary_script = scripts[-1].split("          PY", 1)[0]
        compile(dedent(summary_script), "matrix-job-summary", "exec")
