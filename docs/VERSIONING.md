# Version Policy

PluginMatrix is early-stage software. Versions use `MAJOR.MINOR.PATCH` notation:

- `MAJOR`: reserved for a future stable contract with intentionally incompatible changes.
- `MINOR`: an early-stage milestone that adds or materially changes user-visible capability or repository readiness. Before 1.0, a minor version may include breaking changes when clearly documented.
- `PATCH`: backward-compatible fixes, diagnostics, documentation corrections, and maintenance within a milestone.

A safety patch can reject previously accepted inputs that cannot produce trustworthy evidence. v0.5.1 explicitly rejects zero stability, conflicting output/input paths, ambiguous descriptors and legacy probe snapshots; it does not change the supported platforms or add Matrix features.

The single authoritative version is `pluginmatrix.__version__` in `pluginmatrix/__init__.py`. `pyproject.toml` reads that attribute dynamically; it must not contain a second literal project version. CLI `--version`, wheel metadata, sdist metadata, and JSON reports derive from the same value.

Unreleased work for the next minor version uses the PEP 440 suffix `.devN`. The multi-provider development line is `0.6.0.dev0`; it does not replace the public stable `0.5.1` release. Move to a release candidate or final literal only as part of an explicitly authorized Release Gate. This development task creates no tags or published packages.

`CHANGELOG.md` may describe an implemented version as **Unreleased**. Updating the version or changelog does not create a release. A formal release would additionally require the owner-approved release checklist, a deliberate tag/Release decision, and any selected distribution channel. PluginMatrix currently has no published PyPI release policy or automated release workflow.
