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
