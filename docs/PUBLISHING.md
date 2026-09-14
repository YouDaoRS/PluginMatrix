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

Future standalone executables remain a separate GitHub Release asset family and do not change the Python package version or PyPI contents. When implemented, use explicit platform/architecture names such as:

```text
pluginmatrix-<version>-windows-x86_64.zip
pluginmatrix-<version>-linux-x86_64.tar.gz
pluginmatrix-<version>-macos-x86_64.tar.gz
pluginmatrix-<version>-macos-arm64.tar.gz
SHA256SUMS.txt
```

Generate each platform artifact in an isolated platform job, preserve its build provenance and checksum, and attach it to the existing matching GitHub Release only after the same release gate. Do not upload executables, archives, JREs or GUI bundles to PyPI, and do not add GUI functionality merely to create this packaging structure.
