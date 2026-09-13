"""Build project-owned provider fixtures from auditable source."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


FIXTURES = {
    "smoke": "PluginMatrixSmoke.jar",
    "enable-failure": "PluginMatrixEnableFailure.jar",
    "folia-success": "PluginMatrixFoliaSuccess.jar",
    "folia-unsupported": "PluginMatrixFoliaUnsupported.jar",
    "folia-enable-failure": "PluginMatrixFoliaEnableFailure.jar",
}


def paper_classpath(paper_jar: Path, destination: Path) -> str:
    from pluginmatrix.probe import _extract_paper_libraries
    return _extract_paper_libraries(paper_jar, destination)


def build_fixture(root: Path, fixture: str, output: Path, javac: str, classpath: str) -> None:
    source_root = root / fixture / "src"
    sources = sorted(source_root.rglob("*.java"))
    if not sources:
        raise RuntimeError(f"fixture {fixture!r} has no Java source")
    with tempfile.TemporaryDirectory(prefix=f"pluginmatrix-{fixture}-") as temporary:
        classes = Path(temporary) / "classes"
        classes.mkdir()
        command = [javac, "--release", "17", "-cp", classpath, "-d", str(classes)]
        command.extend(str(source) for source in sources)
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if completed.returncode:
            raise RuntimeError((completed.stderr or completed.stdout or "javac failed").strip())
        with ZipFile(output, "w", ZIP_DEFLATED) as archive:
            descriptor = (root / fixture / "plugin.yml").read_text(encoding="utf-8").replace("\r\n", "\n")
            write_entry(archive, "plugin.yml", descriptor.encode("utf-8"))
            for class_file in sorted(classes.rglob("*.class")):
                write_entry(archive, class_file.relative_to(classes).as_posix(), class_file.read_bytes())


def write_entry(archive: ZipFile, name: str, content: bytes) -> None:
    entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    entry.compress_type = ZIP_DEFLATED
    entry.create_system = 3
    entry.external_attr = 0o100644 << 16
    archive.writestr(entry, content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-jar", required=True, type=Path)
    parser.add_argument("--javac", default=shutil.which("javac") or "javac")
    parser.add_argument('--output-dir', type=Path, help='build into a separate directory')
    parser.add_argument('--fixture', action='append', choices=FIXTURES, help='select specific fixtures; default all')
    args = parser.parse_args(argv)
    paper_jar = args.paper_jar.resolve()
    if not paper_jar.is_file():
        parser.error(f"Paper server JAR not found: {paper_jar}")
    root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="pluginmatrix-paper-libraries-") as temporary:
        classpath = paper_classpath(paper_jar, Path(temporary))
        for fixture in args.fixture or FIXTURES:
            filename = FIXTURES[fixture]
            output = (args.output_dir or root) / filename
            output.parent.mkdir(parents=True, exist_ok=True)
            build_fixture(root, fixture, output, args.javac, classpath)
            print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
