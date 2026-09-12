import unittest
from pathlib import Path
from textwrap import dedent

from pluginmatrix.preflight import inspect_plugin


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
        self.assertIn("ci-fixtures/build_fixtures.py", workflow)
        self.assertIn('python -m pip install -e ".[release]"', workflow)
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
        self.assertIn("expected a repository-relative", workflow)
        self.assertIn('cp -- "$PLUGIN_JAR" .ci/plugin.jar', workflow)
        self.assertIn('document["plugin"] = "plugin.jar"', workflow)
        self.assertIn('options["work_dir"] = "../.pluginmatrix/runs"', workflow)
        self.assertIn('options["report"] = "../.pluginmatrix/matrix-report.json"', workflow)
        self.assertIn("if: steps.prepare.outputs.exit_code == '0'", workflow)
        self.assertIn("python -m pluginmatrix matrix .ci/matrix.json", workflow)
        self.assertIn("actions/checkout@v7", workflow)
        self.assertIn("actions/setup-python@v7", workflow)
        self.assertIn("actions/setup-java@v6", workflow)
        self.assertIn("actions/upload-artifact@v7", workflow)
        self.assertIn("pluginmatrix-matrix-report", workflow)
        self.assertIn("pluginmatrix-runtime-artifacts", workflow)
        self.assertIn("GITHUB_STEP_SUMMARY", workflow)
        self.assertIn('python -m pluginmatrix.github_summary "$MATRIX_REPORT" "$GITHUB_STEP_SUMMARY"', workflow)
        self.assertIn("if: always()", workflow)
        self.assertIn(".pluginmatrix/runs/**/result.json", workflow)
        self.assertIn(".pluginmatrix/runs/**/server.log", workflow)
        self.assertIn("if-no-files-found: warn", workflow)
        self.assertNotIn("pull_request_target", workflow)

    def test_workflows_do_not_use_deprecated_node20_action_versions(self):
        workflows = self.read("ci.yml") + self.read("matrix.yml")
        for deprecated in (
            "actions/checkout@v4",
            "actions/setup-python@v5",
            "actions/setup-java@v4",
            "actions/upload-artifact@v4",
        ):
            self.assertNotIn(deprecated, workflows)
        self.assertIn("actions/checkout@v7", self.read("ci.yml"))
        self.assertIn("actions/setup-python@v7", self.read("ci.yml"))

    def test_manual_example_is_valid_json_and_java_17(self):
        import json

        config = json.loads((ROOT / "examples" / "ci-matrix.json").read_text(encoding="utf-8"))
        self.assertEqual(config["plugin"], "../ci-fixtures/PluginMatrixSmoke.jar")
        self.assertTrue(config["environments"])
        self.assertTrue(all(str(item["java"]) == "17" for item in config["environments"]))

    def test_owned_success_fixture_is_valid(self):
        metadata, _ = inspect_plugin(ROOT / "ci-fixtures" / "PluginMatrixSmoke.jar")
        self.assertEqual(metadata["plugin_name"], "PluginMatrixSmoke")
        self.assertEqual(metadata["main_class_java_target"], "17")

    def test_owned_enable_failure_fixture_and_hosted_config_are_valid(self):
        import json

        config = json.loads((ROOT / "examples" / "ci-enable-failure-matrix.json").read_text(encoding="utf-8"))
        self.assertEqual(config["environments"], [{"paper": "1.20.1", "java": 17, "paper_build": 196}])
        metadata, _ = inspect_plugin(ROOT / "ci-fixtures" / "PluginMatrixEnableFailure.jar")
        self.assertEqual(metadata["plugin_name"], "PluginMatrixEnableFailure")
        self.assertEqual(metadata["main_class_java_target"], "17")
        source = (
            ROOT
            / "ci-fixtures"
            / "enable-failure"
            / "src"
            / "pluginmatrix"
            / "fixture"
            / "EnableFailurePlugin.java"
        ).read_text(encoding="utf-8")
        self.assertIn("Intentional PluginMatrix enable failure fixture", source)

    def test_manual_matrix_embedded_python_is_valid(self):
        workflow = self.read("matrix.yml")
        marker = "          python - <<'PY'\n"
        scripts = workflow.split(marker)[1:]
        self.assertEqual(len(scripts), 1)
        for index, script in enumerate(scripts):
            compile(dedent(script.split("          PY", 1)[0]), f"matrix-embedded-{index}", "exec")
