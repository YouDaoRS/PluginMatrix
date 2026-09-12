# v0.5.0 Release Checklist

Preparation date: 2026-09-12

Release-preparation baseline: `f6efc58b5e3af5c1bc42d1292d1d3fbd947b308f`

This checklist separates completed technical preparation from decisions that only the project owner can make. Completing the technical section does not authorize a commit, tag, GitHub Release, upload, or PyPI publication.

## Completed technical preparation

- [x] The authoritative version is `pluginmatrix.__version__ = "0.5.0"`; `pyproject.toml` reads it dynamically and contains no duplicate literal project version.
- [x] `CHANGELOG.md` uses the formal ISO date `2026-09-12` for `0.5.0`; README, STATUS, product scope, public governance files, and package metadata were reviewed for release consistency.
- [x] `LICENSE` contains the Apache License 2.0 text without an invented copyright holder; package metadata uses the SPDX expression `Apache-2.0` and includes `LICENSE`.
- [x] The repository-provided success and enable-failure fixtures each have adjacent Java source, `plugin.yml`, a documented purpose, a deterministic build script, and a recorded SHA-256 checksum.
- [x] Each fixture JAR contains only `plugin.yml` and its compiled fixture class, with no shaded dependency; both JARs rebuild byte-for-byte from Paper 1.20.1/build 196 compile-time libraries on the verified JDK 17 environment.
- [x] The complete 58-test offline suite and `compileall` pass.
- [x] `python -m build` produces the expected sdist and wheel; archive contents and `PKG-INFO`/`METADATA` were inspected.
- [x] A fresh virtual environment installs the exact local wheel, and both installed entry points report `0.5.0`; installed `test --help` and `matrix --help` pass.
- [x] Existing GitHub-hosted success and expected-failure Matrix evidence was reviewed; this preparation did not trigger a workflow.
- [x] `git diff --check` passes, and no generated build product, cache, log, runtime directory, virtual environment, or `__pycache__` content is tracked.

Local artifact names and SHA-256 values belong in the release-preparation report. Rebuild from the final tagged revision and record new hashes if any source file changes or if artifacts are regenerated.

## Project-owner decisions recorded

- [x] The project owner confirmed the right to release both fixture source trees and both fixture JARs under Apache-2.0 for v0.5.0. Repository provenance and reproducible builds remain evidence rather than an independent legal determination.
- [x] The project owner approved the root Apache-2.0 licensing choice and confirmed the intended repository-license presentation.
- [x] The project owner confirmed GitHub Private Vulnerability Reporting is enabled and that the **Report a vulnerability** path referenced by `SECURITY.md` is available.
- [x] The project owner authorized creation of the release commit, creation/push of tag `v0.5.0`, and creation of the GitHub Release.
- [x] The selected release channel is GitHub only. PyPI publication is explicitly excluded from v0.5.0.
- [x] Release notes must retain the documented `PASS` limitation and must not claim complete plugin compatibility.

These decisions apply only to v0.5.0 and do not authorize v0.6 work or PyPI upload.

## Tag and GitHub Release

Perform these steps only after all owner confirmations above and after the release-preparation edits have been reviewed and deliberately committed.

1. From the intended release commit, confirm `git status --short` is empty and record `git rev-parse HEAD`.
2. Re-run the offline suite, `compileall`, fixture rebuild/checksum comparison, `python -m build`, archive inspection, fresh-wheel installation, all required CLI checks, and `git diff --check`.
3. Confirm `CHANGELOG.md`, `docs/STATUS.md`, package metadata, and CLI output all say `0.5.0`.
4. Create annotated tag `v0.5.0` on the verified commit and inspect it locally.
5. Push the approved release commit and tag.
6. Create the GitHub Release from `v0.5.0`, using the `0.5.0` changelog entry as the basis for release notes. Attach only artifacts rebuilt from that exact tag and include their SHA-256 values.
7. Confirm the GitHub Release page shows the intended tag, commit, notes, and artifact checksums.

## PyPI publication — excluded

Do not upload v0.5.0 to PyPI or TestPyPI. A future decision to add a package index is separate work and is not authorized by this checklist.

## Post-release verification

- [ ] Install `pluginmatrix==0.5.0` from the selected public package index in a new environment, not from the repository or local wheel cache.
- [ ] Run `pluginmatrix --version`, `python -m pluginmatrix --version`, `pluginmatrix test --help`, and `pluginmatrix matrix --help`.
- [ ] Verify the GitHub tag, Release, changelog, README links, license detection, issue forms, contribution guide, security reporting route, and published package project URLs are publicly reachable and consistent.
- [ ] Verify the public sdist/wheel names, sizes, SHA-256 values, and metadata match the release record.
- [ ] Confirm no source archive or wheel contains fixture JARs, Paper/Mojang/JDK artifacts, third-party plugin JARs, caches, logs, `.pluginmatrix`, build directories, or virtual environments.
- [ ] If a post-release defect is found, document it without rewriting `v0.5.0`; use a separately approved patch release rather than modifying the existing tag or artifacts.
