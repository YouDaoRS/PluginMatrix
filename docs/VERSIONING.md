# Version Policy

PluginMatrix is early-stage software. Versions use `MAJOR.MINOR.PATCH` notation:

- `MAJOR`: reserved for a future stable contract with intentionally incompatible changes.
- `MINOR`: an early-stage milestone that adds or materially changes user-visible capability or repository readiness. Before 1.0, a minor version may include breaking changes when clearly documented.
- `PATCH`: backward-compatible fixes, diagnostics, documentation corrections, and maintenance within a milestone.

A safety patch can reject previously accepted inputs that cannot produce trustworthy evidence. v0.5.1 explicitly rejects zero stability, conflicting output/input paths, ambiguous descriptors and legacy probe snapshots; it does not change the supported platforms or add Matrix features.

The single authoritative version is `pluginmatrix.__version__` in `pluginmatrix/__init__.py`. `pyproject.toml` reads that attribute dynamically; it must not contain a second literal project version. CLI `--version`, wheel metadata, sdist metadata, and JSON reports derive from the same value.

Unreleased work for the next minor version uses the PEP 440 suffix `.devN`; current source development is `0.7.0.dev1`. After an explicitly authorized Release Candidate Gate, a release candidate uses `MAJOR.MINOR.PATCHrcN`. The current public stable release is `0.6.0`; moving to a final literal, creating a tag or publishing any package requires a separate owner-authorized release operation.

`CHANGELOG.md` may describe an implemented version as **Unreleased**. Updating the version or changelog does not create a release. A formal release additionally requires the owner-approved release checklist, a deliberate tag/Release decision, and approval for every selected distribution channel. PyPI files are immutable: never rebuild or retry an existing version with different bytes. The Trusted Publishing workflow may publish only the already verified GitHub Release wheel and sdist for that tag; TestPyPI validation and explicit owner confirmation precede formal PyPI approval.
