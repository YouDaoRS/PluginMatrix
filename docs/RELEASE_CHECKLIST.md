# Release Checklist

Run this checklist from a clean checkout. It is deliberately manual while PluginMatrix remains early-stage. Completing it does not itself authorize a PyPI upload, Git tag, or GitHub Release.

## Repository and legal review

- [ ] `git status --short` is empty and the intended revision is recorded.
- [ ] The project owner has approved the root license and any copyright statement actually used.
- [ ] `THIRD_PARTY_NOTICES.md` and `docs/THIRD_PARTY_REVIEW.md` match all code, fixtures, JARs, documentation, and workflows in the tree.
- [ ] Every binary fixture has adjacent auditable source, a build method, a purpose, and a current checksum; no third-party JAR lacks explicit redistribution permission.
- [ ] No secrets, private logs, server data, `.pluginmatrix`, cache, run, `__pycache__`, egg-info, build, or virtual-environment content is tracked.

## Version, docs, and examples

- [ ] `pluginmatrix/__init__.py` contains the intended version; `pyproject.toml` uses the dynamic attribute and contains no duplicate literal version.
- [ ] `pluginmatrix --version`, `python -m pluginmatrix --version`, wheel metadata, reports, `CHANGELOG.md`, and `docs/STATUS.md` agree.
- [ ] README commands, verdict meaning, requirements, paths, troubleshooting, hosted workflow inputs, and privacy warnings match the current CLI.
- [ ] `examples/matrix.json` and both hosted example configs reference only repository-owned fixtures and resolve paths relative to their files.

## Offline verification

```powershell
python -m unittest discover -s tests -v
python -m compileall pluginmatrix tests ci-fixtures/build_fixtures.py
```

- [ ] All tests pass without Paper downloads or a server start.
- [ ] `compileall` passes.

## Distribution and clean installation

Use a temporary directory or disposable virtual environment; do not reuse an editable install.

```powershell
python -m venv <temp>\build-venv
<temp>\build-venv\Scripts\python -m pip install ".[release]"
<temp>\build-venv\Scripts\python -m build --sdist --wheel --outdir <temp>\dist .
```

- [ ] Both sdist and wheel build successfully.
- [ ] Archive listings contain the expected package, README, license, notices, docs/examples/tests where intended, and no local caches, runs, `__pycache__`, egg-info source tree, build output, or unauthorized binary fixtures.
- [ ] In a second fresh venv, install the wheel by exact local path with no editable source and run:

```powershell
pluginmatrix --version
pluginmatrix --help
python -m pluginmatrix --version
python -m pluginmatrix test --help
python -m pluginmatrix matrix --help
```

## Hosted smoke before a real release

- [ ] Manually run the Java 17 `Compatibility Matrix` success case with `examples/ci-matrix.json` and `ci-fixtures/PluginMatrixSmoke.jar`.
- [ ] Manually run the expected failure case with `examples/ci-enable-failure-matrix.json` and `ci-fixtures/PluginMatrixEnableFailure.jar`.
- [ ] Confirm success/failure verdicts and summaries, zero unexpected warnings, and both artifacts on each run.
- [ ] Record run URLs and the exact commit in `docs/STATUS.md`; do not reinterpret `PASS` as complete gameplay compatibility.

## Final artifact check

- [ ] Inspect final archive names, sizes, SHA-256 values, METADATA/PKG-INFO, entry lists, and installed command output.
- [ ] Remove or ignore temporary local build products without deleting user caches or unrelated files.
- [ ] Obtain explicit owner authorization before any PyPI upload, GitHub Release, or tag/push.
