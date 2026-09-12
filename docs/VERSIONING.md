# Version Policy

PluginMatrix is early-stage software. Versions use `MAJOR.MINOR.PATCH` notation:

- `MAJOR`: reserved for a future stable contract with intentionally incompatible changes.
- `MINOR`: an early-stage milestone that adds or materially changes user-visible capability or repository readiness. Before 1.0, a minor version may include breaking changes when clearly documented.
- `PATCH`: backward-compatible fixes, diagnostics, documentation corrections, and maintenance within a milestone.

The single authoritative version is `pluginmatrix.__version__` in `pluginmatrix/__init__.py`. `pyproject.toml` reads that attribute dynamically; it must not contain a second literal project version. CLI `--version`, wheel metadata, sdist metadata, and JSON reports derive from the same value.

`CHANGELOG.md` may describe an implemented version as **Unreleased**. Updating the version or changelog does not create a release. A formal release would additionally require the owner-approved release checklist, a deliberate tag/Release decision, and any selected distribution channel. PluginMatrix currently has no published PyPI release policy or automated release workflow.
