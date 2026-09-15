from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_ARTIFACT = "pluginmatrix-matrix-report"
RUNTIME_ARTIFACT = "pluginmatrix-runtime-artifacts"


def _cell(value: object, fallback: str = "unknown") -> str:
    text = str(value) if value not in (None, "") else fallback
    return text.replace("`", "'").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _evidence_text(environment: dict[str, Any]) -> str:
    artifacts = environment.get("artifacts")
    if not isinstance(artifacts, dict):
        artifacts = {}
    primary = environment.get("primary_evidence")
    if primary:
        return _cell(primary)
    for key in ("runtime_report", "server_log", "run_dir"):
        if artifacts.get(key):
            return _cell(artifacts[key])
    return "not generated"


def render_job_summary(report_path: Path) -> str:
    lines = ["## PluginMatrix Compatibility Matrix", ""]
    if not report_path.is_file():
        lines.extend(
            [
                f"Matrix report was not generated at `{_cell(report_path)}`.",
                "",
                "Check configuration/setup errors in the job log. Runtime artifacts may not exist if Matrix did not start.",
            ]
        )
        return "\n".join(lines) + "\n"

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        lines.extend(
            [
                f"Matrix report could not be read as valid JSON: `{_cell(type(exc).__name__)}: {_cell(exc)}`.",
                "",
                f"Check `{RUNTIME_ARTIFACT}` and configuration/setup errors in the job log.",
            ]
        )
        return "\n".join(lines) + "\n"
    if not isinstance(report, dict):
        lines.extend(
            [
                "Matrix report has an unexpected format; expected a JSON object.",
                "",
                f"Check `{RUNTIME_ARTIFACT}` and configuration/setup errors in the job log.",
            ]
        )
        return "\n".join(lines) + "\n"

    plugin = report.get("plugin")
    stats = report.get("summary")
    environments = report.get("environments")
    if not isinstance(plugin, dict):
        plugin = {}
    if not isinstance(stats, dict):
        stats = {}
    if not isinstance(environments, list):
        environments = []

    lines.extend(
        [
            f"**Plugin:** {_cell(plugin.get('plugin_name') or plugin.get('plugin_jar'))}",
            "",
            "| Environment | Verdict | Behavior | Failure stage | Primary evidence |",
            "|---|---|---|---|---|",
        ]
    )
    for environment in environments:
        if not isinstance(environment, dict):
            continue
        verdict = environment.get("verdict")
        stage = environment.get("failure_stage") or ("—" if verdict == "PASS" else "unknown")
        behavior = environment.get('behavior')
        behavior = behavior if isinstance(behavior, dict) else {}
        lines.append(
            f"| `{_cell(environment.get('id'))}` | `{_cell(verdict)}` | `{_cell(behavior.get('verdict'), 'NOT_RUN')}` | `{_cell(stage)}` | "
            f"`{_evidence_text(environment)}` |"
        )

    lines.extend(
        [
            "",
            f"**Summary:** {_cell(stats.get('passed'), '0')} passed, {_cell(stats.get('failed'), '0')} failed "
            f"of {_cell(stats.get('total'), '0')}",
        ]
    )
    failures = [
        environment
        for environment in environments
        if isinstance(environment, dict) and not environment.get('verification_passed', environment.get('verdict') == 'PASS')
    ]
    if failures:
        lines.extend(["", "### Failures", ""])
        for environment in failures:
            behavior = environment.get('behavior')
            behavior = behavior if isinstance(behavior, dict) else {}
            lines.append(
                f"- `{_cell(environment.get('id'))}` — `{_cell(environment.get('verdict'), 'UNKNOWN_FAILURE')}` "
                f"at `{_cell(environment.get('failure_stage'))}`: {_cell(environment.get('reason'), 'No reason recorded')}. "
                f"Behavior: `{_cell(behavior.get('verdict'), 'NOT_RUN')}` {_cell(behavior.get('reason'), '')}. "
                f"Evidence: `{_evidence_text(environment)}`"
            )
    lines.extend(
        [
            "",
            f"Artifacts: `{REPORT_ARTIFACT}`, `{RUNTIME_ARTIFACT}`",
            f"Matrix report path: `{_cell(report_path)}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a GitHub Job Summary from a PluginMatrix report.")
    parser.add_argument("report", type=Path)
    parser.add_argument("summary", type=Path)
    args = parser.parse_args(argv)
    content = render_job_summary(args.report)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    with args.summary.open("a", encoding="utf-8") as output:
        output.write(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
