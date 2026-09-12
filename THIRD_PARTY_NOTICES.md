# Third-Party Notices and Sources

The PluginMatrix Python package uses only the Python standard library and does not bundle Paper, a JDK, or third-party plugin code.

## Downloaded at runtime

PluginMatrix queries the official Paper API and downloads the selected Paper server artifact. The artifact is stored in the user's cache, is not part of the Python wheel or source distribution, and remains subject to Paper's and its dependencies' own terms. Paper bootstrap may download additional Mojang runtime files.

## Repository fixtures

`PluginMatrixSmoke.jar` and `PluginMatrixEnableFailure.jar` are generated from the original source, descriptors, and build script under `ci-fixtures/`. They contain no shaded dependencies. Paper API libraries are used only as a compile-time classpath and are not copied into either JAR.

An `EnhancedFly-2.2.0.jar` previously used for v0.4 hosted validation was removed during the v0.5 audit. Its embedded `plugin.yml` named the same GitHub account as author, but neither this repository nor the adjacent source checkout contained an explicit license or other redistribution grant. That evidence is insufficient for a public repository to redistribute the binary. Historical validation facts remain documented; public examples now use the owned smoke fixture.

## Referenced projects

`docs/THIRD_PARTY_REVIEW.md` records projects consulted for high-level design comparison. No code, workflow, tests, comments, or file structure was copied from those projects. In particular, no GPL-3.0 material was copied.

The repository's GitHub workflows reference official GitHub Actions by version. Those actions execute on GitHub-hosted runners and are not vendored into this repository.
