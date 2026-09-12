# Changelog

PluginMatrix follows the version policy in `docs/VERSIONING.md`. No entry below implies that a Git tag, GitHub Release, or PyPI release exists. Earlier entries without dates were development milestones rather than formal releases.

## 0.5.0 — 2026-09-12

- Prepared the repository for public source review without adding runtime-verification capability.
- Added governance, contribution, security, issue, pull-request, source-audit, versioning, and release-checklist documentation.
- Made `pluginmatrix.__version__` the packaging version source and expanded package metadata.
- Replaced the publicly stored EnhancedFly JAR and examples with repository-provided success and enable-failure fixtures whose source, descriptors, build method, and checksums are retained; the project owner confirmed their Apache-2.0 release rights for v0.5.0.
- Added offline release-readiness tests and clean sdist/wheel/install verification.

## 0.4.0 — Implemented, not formally released

- Added Matrix preflight checks for plugin metadata, Java/JDK availability, output paths, conflicts, and configuration diagnostics.
- Added direct failure-stage, reason, artifact, and primary-evidence output to Matrix CLI, Matrix Report, and GitHub Job Summary.
- Upgraded the official GitHub Actions to Node.js 24-compatible major versions.
- Hosted Matrix #3 passed on Paper 1.20.1/build 196/Java 17; Matrix #4 exercised a real owned `onEnable()` failure and retained artifacts. Both runs had zero Action deprecation warnings.

## 0.3.0 — Implemented, not formally released

- Added offline push/pull-request CI.
- Added a manual Java 17 Compatibility Matrix workflow that preserves report and runtime artifacts on success or failure.
- Added tested Job Summary rendering from the Matrix Report rather than duplicating verdict logic.

## 0.2.0 — Implemented, not formally released

- Added JSON-configured sequential Compatibility Matrix execution over one plugin JAR.
- Added full pre-execution config validation, isolated per-environment runs, a unified Matrix Report, and stable Matrix exit codes.

## 0.1.0 — Implemented, not formally released

- Added plugin-JAR preflight, Paper artifact resolution and checksum verification, isolated real Paper startup, Java validation, lifecycle evidence, runtime probe confirmation, raw `server.log`, and structured runtime reports.
- Defined stable verdicts that distinguish environment, server startup, plugin discovery, load, enable, disable, pass, and unknown failures.
