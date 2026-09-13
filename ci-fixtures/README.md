# Repository runtime fixtures

Both committed fixture JARs can be rebuilt solely from source in this directory:

- `PluginMatrixSmoke.jar` enables successfully.
- `PluginMatrixEnableFailure.jar` intentionally throws from `onEnable()`.

They contain no shaded dependencies. Compilation uses JDK 17 and the API libraries embedded in the official Paper 1.20.1/build 196 server JAR; those Paper libraries are compile-only and are not copied into the fixtures.

Rebuild from the repository root after obtaining the official Paper server JAR through PluginMatrix or Paper:

```powershell
python .\ci-fixtures\build_fixtures.py --paper-jar .\.pluginmatrix\cache\paper-1.20.1-196.jar
Get-FileHash -Algorithm SHA256 .\ci-fixtures\PluginMatrixSmoke.jar, .\ci-fixtures\PluginMatrixEnableFailure.jar
```

The build script fixes JAR entry order, timestamps, permissions, and descriptor line endings. With the same JDK compiler output, repeated builds match `SHA256SUMS.txt`; if a different JDK produces different class bytes, audit the two listed entries and source before updating the checksums. Each JAR contains only its compiled fixture class and `plugin.yml`. These fixtures are not production plugins.

The adjacent source, descriptors, build process, JAR contents, and checksums are repository provenance evidence; they do not by themselves establish legal ownership. The project owner confirmed the right to release both fixture source trees and JARs under Apache-2.0 for v0.5.0.

## v0.6 Folia source fixtures

The new project-authored source fixtures `folia-success`, `folia-unsupported`, and `folia-enable-failure` respectively declare support and enable, omit the declaration, or declare support and throw during enable. They are authored in this repository, not copied from a third-party plugin. These minimal fixtures exercise acceptance/lifecycle only; they do not test region or thread safety.

Build all five into ignored local output (do not commit build artifacts):

```powershell
python ci-fixtures/build_fixtures.py --paper-jar .pluginmatrix/cache/paper-1.20.1-196.jar --output-dir .pluginmatrix/fixtures
```

`examples/mixed-matrix.json` expects the resulting `PluginMatrixFoliaSuccess.jar`. The original two committed fixture JARs and checksums remain unchanged. New gate artifacts carry their own hashes in runtime JSON. For a targeted build, repeat `--fixture folia-success`/`--fixture folia-unsupported`/`--fixture folia-enable-failure`. The real provider gate compiles all five from source into its unique gate directory using the provided JDK and official API libraries; no API library is redistributed.
