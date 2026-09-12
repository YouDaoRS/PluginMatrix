# Contributing to PluginMatrix

PluginMatrix is an early-stage Python 3.10+ CLI focused only on pre-release runtime verification for Minecraft Paper plugins. Keep changes within the boundaries in `AGENTS.md` and `docs/PRODUCT_SPEC.md`; propose scope changes in an issue before implementing them.

## Development setup

From a clean checkout, create and activate a virtual environment, then install the project:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[release]"
```

On Linux or macOS, use `.venv/bin/python` instead. The `release` extra contains packaging tools used by release-readiness tests; PluginMatrix itself has no third-party runtime dependencies.

Run the offline checks before opening a pull request:

```powershell
python -m unittest discover -s tests -v
python -m compileall pluginmatrix tests ci-fixtures/build_fixtures.py
```

These checks must not download Paper or start a server. Changes to runtime verdict logic also need focused tests for the affected success or failure state and, when practical, a real isolated Paper validation.

## Issues and pull requests

- Search existing issues first and use the repository templates.
- Keep a pull request focused and explain behavior changes, evidence, and tests.
- Preserve stable verdicts, failure stages, raw `server.log`, and report compatibility unless the change is explicitly approved.
- Do not add third-party plugin JARs, credentials, server data, `.pluginmatrix` output, caches, or build artifacts.
- Only add code and assets you have the right to contribute. Record the source, revision, license, and modifications for any reused material.
- Never copy GPL-3.0 code, workflow, tests, comments, or file structure into this project.

Runtime reports and logs can contain local paths, usernames, IP addresses, plugin names, configuration values, and stack traces. Redact secrets and personal or server data before posting them. Do not upload a third-party plugin JAR unless its license explicitly permits redistribution.

By submitting a contribution, you represent that you have the right to provide it under the repository's license. No contributor license agreement is currently required.
