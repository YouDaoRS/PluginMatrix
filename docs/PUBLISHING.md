# Publishing channels

PluginMatrix uses one release identity across its distribution channels. PyPI is the installation index for the Python CLI; GitHub Release is the authoritative source, asset and checksum record.

## Python CLI release flow

1. Complete the release checklist and create an immutable tag and GitHub Release from the approved commit.
2. Build wheel and sdist once from clean archived tag source. Inspect their contents and metadata, record SHA-256, and attach those exact files to the GitHub Release.
3. Run `.github/workflows/publish-pypi.yml` with `target=testpypi`. The workflow downloads—not rebuilds—the GitHub Release assets and verifies the release target, tag commit, exact filenames, package name/version and GitHub asset digests before Trusted Publishing.
4. Verify a fresh pipx installation from TestPyPI. Record the index files and hashes.
5. Present the project name, version, asset hashes and Trusted Publisher identity to the owner. Formal PyPI upload requires explicit approval and the protected `pypi` GitHub Environment review.
6. Run the same workflow with `target=pypi`, verify the public index hashes, then validate `pipx install`, CLI/version/providers and `pipx upgrade` in a fresh isolated pipx home.

Trusted Publishers are restricted to repository `YouDaoRS/PluginMatrix`, workflow filename `publish-pypi.yml`, and the matching `testpypi` or `pypi` Environment. The workflow has only `contents: read` and `id-token: write`, uses no stored PyPI credential, refuses draft/prerelease GitHub Releases and sets `skip-existing: false`. PyPI versions and files are never replaced.

## Standalone application assets

Standalone executables are a separate GitHub Release asset family and do not change the Python package version or PyPI contents. PyInstaller `onedir` bundles are built and tested on the matching native platform; PyInstaller is not a cross-compiler. Use explicit platform/architecture names such as:

```text
pluginmatrix-<version>-windows-x86_64.zip
pluginmatrix-<version>-linux-x86_64.tar.gz
pluginmatrix-<version>-macos-x86_64.tar.gz
pluginmatrix-<version>-macos-arm64.tar.gz
SHA256SUMS.txt
```

Generate each platform artifact in an isolated platform job, preserve its build provenance and checksum, and attach it to the existing matching GitHub Release only after the same release gate. Do not upload executables, archives, JREs or GUI bundles to PyPI, and do not add GUI functionality merely to create this packaging structure.

`.github/workflows/standalone.yml` builds Windows x86-64, Linux x86-64, macOS x86-64 and macOS arm64 archives. Every job checks the frozen version, Provider registry, Java/Javac access, local Web UI resources, and one real Paper/probe/report/log path. `BUILD-INFO.json`, `LICENSE`, `THIRD_PARTY_NOTICES.md`, and `PYTHON-LICENSE.txt` are included; the Python license comes from the build interpreter when exposed and otherwise from the repository's canonical CPython license copy, with the source recorded in build metadata. JARs are rejected by the archive audit. The workflow only uploads CI artifacts and combined checksums. It never creates a tag, GitHub Release, signature, installer, notarization, update channel, or PyPI upload.

The PyPI workflow downloads wheel and sdist by exact versioned names rather than wildcarding `*.tar.gz`, so standalone tarballs attached to a future matching GitHub Release cannot enter or disrupt the Python-package publication set.
