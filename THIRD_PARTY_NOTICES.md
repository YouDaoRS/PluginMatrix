# Third-Party Notices and Sources

The PluginMatrix Python package uses only the Python standard library and does not bundle Paper, a JDK, or third-party plugin code.

Standalone archives are built with PyInstaller and include the platform's CPython interpreter and standard library. Each archive includes `PYTHON-LICENSE.txt`: the builder prefers the exact interpreter's license file and otherwise uses the canonical CPython license vendored at `standalone/licenses/CPYTHON-LICENSE.txt`. Native libraries copied for CPython modules are covered by `NATIVE-LICENSES.txt`, including OpenSSL, bzip2, libffi, XZ/liblzma, libuuid and zlib notices used by the hosted targets. `BUILD-INFO.json` names the Python and PyInstaller versions, records the Python license source, and lists every license file. PyInstaller's GPL exception permits distribution of the generated bundle under the application's license; PyInstaller itself is a build dependency and is not installed by the bundle. See the [PyInstaller license](https://pyinstaller.org/en/stable/license.html), [Python license](https://docs.python.org/3/license.html), and the [upstream CPython 3.11 license source](https://github.com/python/cpython/blob/3.11/LICENSE).

Standalone archives do not include Java, Paper, Purpur, Folia, or plugin JARs. Those remain installed/provided or downloaded at runtime under their own terms.

## Downloaded at runtime

PluginMatrix queries the official Paper API and downloads the selected Paper server artifact. The artifact is stored in the user's cache, is not part of the Python wheel or source distribution, and remains subject to Paper's and its dependencies' own terms. Paper bootstrap may download additional Mojang runtime files.

After an explicit preview and install request, PluginMatrix can query the official Eclipse Adoptium API and download an Eclipse Temurin portable full JDK from the matching `adoptium/temurin*-binaries` GitHub release. The archive is verified against the size and SHA-256 reported by the official API, extracted into the user's managed cache, and is never included in the PluginMatrix wheel, source distribution, standalone archives, or GitHub Release assets. Temurin/OpenJDK binaries carry their own notices and are distributed under GPLv2 with the Classpath Exception; the installed JDK's included `legal` files remain authoritative for that package. See [Eclipse Temurin](https://adoptium.net/temurin/) and the [OpenJDK GPLv2 + Classpath Exception](https://openjdk.org/legal/gplv2+ce.html).

## Repository fixtures

`PluginMatrixSmoke.jar` and `PluginMatrixEnableFailure.jar` can be rebuilt from the adjacent source, descriptors, and build script under `ci-fixtures/`. They contain no shaded dependencies. Paper API libraries are used only as a compile-time classpath and are not copied into either JAR. These are repository provenance facts, not an independent legal ownership determination; the project owner confirmed release rights for both fixture source trees and JARs under Apache-2.0 for v0.5.0.

An `EnhancedFly-2.2.0.jar` previously used for v0.4 hosted validation was removed during the v0.5 audit. Its embedded `plugin.yml` named the same GitHub account as author, but neither this repository nor the adjacent source checkout contained an explicit license or other redistribution grant. That evidence is insufficient for a public repository to redistribute the binary. Historical validation facts remain documented; public examples now use the repository-provided smoke fixture.

Removal refers to the current source tree and release packages, not erasure of historical public objects. On 2026-09-13, a HEAD request to the raw file at commit `c5fe4efedae5156c4e4adf84740e3d8e5d1e72ab` still returned HTTP 200 and Content-Length 17,868,623. The owner must decide how to document redistribution rights or handle historical exposure. No history rewrite, remote deletion or claim of infringement is made by this patch. See `docs/V0.5.1_PREPARATION.md`.

## Referenced projects

`docs/THIRD_PARTY_REVIEW.md` records projects consulted for high-level design comparison. No code, workflow, tests, comments, or file structure was copied from those projects. In particular, no GPL-3.0 material was copied.

The repository's GitHub workflows reference official GitHub Actions by version. Those actions execute on GitHub-hosted runners and are not vendored into this repository.
