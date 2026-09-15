"""Opt-in, portable Temurin JDK store.

No installer, PATH/JAVA_HOME changes, registry edits, shell commands or hooks.
The official archive SHA-256 authenticates downloads against HTTPS metadata.
An extracted-file manifest detects later accidental/tampered cache changes.
OS-locked use leases prevent deletion while any cooperating process uses a JDK.
This does not isolate hostile programs running as the same OS user.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import stat
import tarfile
import tempfile
import time
import uuid
import unicodedata
import zipfile
from contextlib import contextmanager, ExitStack
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlencode, urlsplit, unquote

from .artifacts import read_json, open_official, safe_url
from .control import RunControl, RunCancelled
from .files import atomic_json, read_evidence_bytes, reject_links
from .locking import file_lock

API_HOSTS = {'api.adoptium.net'}
DOWNLOAD_HOSTS = {'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'}
MAX_ARCHIVE = 512 * 1024 * 1024
MAX_EXPANDED = 2 * 1024**3
MAX_FILES = 30000
MAX_RECEIPT = 8 * 1024 * 1024
STORE_MARKER = {'schema': 1, 'owner': 'PluginMatrix managed JDK store'}
IDENTIFIER = re.compile(r'temurin-(?:8|11|16|17|21|25)-(?:windows|linux|mac)-(?:x64|aarch64)-[a-f0-9]{64}')


class JdkSelectionError(ValueError):
    """A managed environment prerequisite failed before invoking the verifier."""


def host_platform() -> tuple[str, str]:
    system = {'Windows': 'windows', 'Linux': 'linux', 'Darwin': 'mac'}.get(platform.system())
    arch = {'amd64': 'x64', 'x86_64': 'x64', 'arm64': 'aarch64', 'aarch64': 'aarch64'}.get(platform.machine().lower())
    if not system or not arch:
        raise ValueError('managed JDKs support Windows/Linux/macOS on x64/aarch64 only')
    return system, arch


def _query(major, system, arch):
    if type(major) is not int or major not in (8, 11, 16, 17, 21, 25):
        raise ValueError('managed JDK major must be one of 8, 11, 16, 17, 21, 25')
    if system not in ('windows', 'linux', 'mac') or arch not in ('x64', 'aarch64'):
        raise ValueError('unsupported managed JDK platform')
    return f'https://api.adoptium.net/v3/assets/feature_releases/{major}/ga?' + urlencode({
        'architecture': arch, 'heap_size': 'normal', 'image_type': 'jdk', 'jvm_impl': 'hotspot',
        'os': system, 'page_size': 1, 'project': 'jdk', 'vendor': 'eclipse', 'sort_order': 'DESC'})


@dataclass(frozen=True)
class JdkPackage:
    major: int
    os: str
    architecture: str
    release: str
    filename: str
    url: str
    sha256: str
    size: int
    api_url: str

    @property
    def id(self):
        return f'temurin-{self.major}-{self.os}-{self.architecture}-{self.sha256}'

    def to_dict(self):
        return {'id': self.id, 'vendor': 'Eclipse Adoptium Temurin', **asdict(self)}

    def validate(self):
        if self.api_url != _query(self.major, self.os, self.architecture):
            raise ValueError('JDK provenance does not match the official query')
        if not isinstance(self.sha256, str) or not re.fullmatch('[a-f0-9]{64}', self.sha256):
            raise ValueError('official JDK SHA-256 is required')
        if type(self.size) is not int or not 0 < self.size <= MAX_ARCHIVE:
            raise ValueError('official JDK archive size must be in (0, 512 MiB]')
        if not isinstance(self.release, str) or not re.fullmatch(r'jdk-?[A-Za-z0-9_.+-]{1,100}', self.release):
            raise ValueError('invalid JDK release identity')
        if not isinstance(self.filename, str) or not re.fullmatch(r'[A-Za-z0-9_.+-]{1,180}', self.filename):
            raise ValueError('invalid JDK archive filename')
        extension = '.zip' if self.os == 'windows' else '.tar.gz'
        if not self.filename.endswith(extension):
            raise ValueError('only portable zip/tar.gz JDK archives are supported')
        safe_url(self.url, {'github.com'})
        parts = urlsplit(self.url)
        expected = f'/adoptium/temurin{self.major}-binaries/releases/download/{self.release}/{self.filename}'
        if unquote(parts.path) != expected or parts.query or parts.fragment:
            raise ValueError('JDK archive URL must identify the official Temurin repository and release')


def resolve_package(major: int, *, system=None, architecture=None) -> JdkPackage:
    host_os, host_arch = host_platform()
    system, architecture = system or host_os, architecture or host_arch
    url = _query(major, system, architecture)
    document = read_json(url, API_HOSTS)
    matches = []
    if not isinstance(document, list) or len(document) != 1:
        raise ValueError('official API did not identify exactly one GA JDK release')
    release = document[0]
    if (not isinstance(release, dict) or release.get('release_type') != 'ga' or release.get('vendor') != 'eclipse'
            or not isinstance(release.get('version_data'), dict) or release['version_data'].get('major') != major
            or not isinstance(release.get('binaries'), list)):
        raise ValueError('official API returned mismatched JDK release metadata')
    for binary in release['binaries']:
        if not isinstance(binary, dict):
            raise ValueError('malformed JDK binary metadata')
        if all(binary.get(k) == v for k, v in {
            'architecture': architecture, 'os': system, 'image_type': 'jdk',
            'jvm_impl': 'hotspot', 'heap_size': 'normal', 'project': 'jdk',
        }.items()):
            matches.append(binary.get('package'))
    if len(matches) != 1 or not isinstance(matches[0], dict):
        raise ValueError('official API did not identify exactly one matching portable JDK')
    p = matches[0]
    package = JdkPackage(major, system, architecture, release.get('release_name'),
                         p.get('name'), p.get('link'), p.get('checksum'), p.get('size'), url)
    package.validate()
    return package


def _relative(name: str) -> str:
    if (not isinstance(name, str) or not name or len(name) > 512 or '\\' in name or ':' in name
            or name.startswith('/') or any(ord(c) < 32 for c in name)):
        raise ValueError('unsafe JDK archive/cache path')
    parts = name.rstrip('/').split('/')
    if any(not part or part in ('.', '..') or part.endswith((' ', '.'))
           or re.match(r'(?i)^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', part)
           for part in parts):
        raise ValueError('unsafe JDK archive/cache path component')
    return '/'.join(parts)


def _checked_child(root: Path, relative: str) -> Path:
    root = root.absolute()
    path = root.joinpath(*_relative(relative).split('/'))
    reject_links(path)
    if not path.resolve().is_relative_to(root.resolve()) or path.resolve() == root.resolve():
        raise ValueError('JDK path escaped the managed root')
    return path


def _hash_regular(path: Path, limit=MAX_EXPANDED) -> tuple[str, int]:
    reject_links(path)
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        info, current = os.fstat(stream.fileno()), path.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit
                or (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino)):
            raise ValueError('JDK cache integrity/size requires bounded regular files without hardlinks or substitution')
        digest, total = hashlib.sha256(), 0
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            total += len(data)
            if total > limit:
                raise ValueError('JDK file exceeds its size limit')
            digest.update(data)
        after = os.fstat(stream.fileno())
        if (info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('JDK file changed during verification')
    return digest.hexdigest(), total


def _tree(root: Path) -> list[Path]:
    reject_links(root)
    if not root.is_dir():
        raise ValueError('managed JDK entry must be a directory')
    files = []
    count = 0
    for parent, directories, names in os.walk(root, followlinks=False):
        for name in [*directories, *names]:
            path = Path(parent) / name
            _relative(path.relative_to(root).as_posix())
            reject_links(path)
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) and not stat.S_ISDIR(info.st_mode):
                raise ValueError('JDK tree contains a special file')
            if stat.S_ISREG(info.st_mode):
                if info.st_nlink != 1:
                    raise ValueError('JDK tree contains a hardlink')
                files.append(path)
            count += 1
            if count > MAX_FILES:
                raise ValueError('JDK tree exceeds the entry limit')
    return files


def _remove_tree(root: Path, path: Path):
    # All recursive removals are confined to one checked managed-store child.
    reject_links(root)
    reject_links(path)
    resolved_root, resolved = root.resolve(), path.resolve()
    if resolved == resolved_root or not resolved.is_relative_to(resolved_root):
        raise ValueError('refusing removal outside the managed JDK store')
    if path.exists():
        _tree(path)  # Reject reparse points, links, hardlinks and special files first.
        shutil.rmtree(path)


def _tar_link_target(name: str, target: str) -> str:
    """Resolve a TAR symlink lexically within its single top-level JDK tree."""
    if (not isinstance(target, str) or not target or len(target) > 512
            or target.startswith('/') or '\\' in target or ':' in target
            or any(ord(c) < 32 for c in target)):
        raise ValueError('unsafe JDK TAR link target')
    parts = name.split('/')[:-1]
    if not parts:
        raise ValueError('JDK TAR link must stay within its top-level directory')
    for part in target.split('/'):
        if part == '..':
            if len(parts) <= 1:
                raise ValueError('JDK TAR link escapes its top-level directory')
            parts.pop()
        elif part != '.':
            parts.append(_relative(part))
    return _relative('/'.join(parts))


def _extract(archive: Path, destination: Path, control: RunControl):
    """Create only regular files; direct internal TAR symlinks become copies."""
    destination.mkdir()
    seen, spelling, expanded = set(), {}, 0

    def reserve(name):
        control.check()
        name = _relative(name)
        key = name.casefold()
        if key in seen or len(seen) >= MAX_FILES:
            raise ValueError('duplicate/case-colliding or excessive JDK archive entries')
        parts = name.split('/')
        for index in range(1, len(parts) + 1):
            prefix = '/'.join(parts[:index])
            if spelling.setdefault(unicodedata.normalize('NFC', prefix).casefold(), prefix) != prefix:
                raise ValueError('case-colliding JDK archive parent paths')
        seen.add(key)
        return name

    def copy(name, size, directory, mode, source, *, reserved=False):
        nonlocal expanded
        control.check()
        name = name if reserved else reserve(name)
        expanded += size
        if size < 0 or expanded > MAX_EXPANDED:
            raise ValueError('JDK archive exceeds 2 GiB expanded limit')
        target = _checked_child(destination, name)
        if directory:
            target.mkdir(parents=True, exist_ok=True)
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            remaining = size
            while remaining:
                control.check()
                data = source.read(min(1024 * 1024, remaining))
                if not data:
                    raise ValueError('truncated JDK archive member')
                stream.write(data)
                remaining -= len(data)
            if source.read(1):
                raise ValueError('JDK archive member exceeds its declared size')
        # Strip special permission bits. No executable installer is ever run.
        target.chmod(0o755 if mode & 0o111 else 0o644)

    if archive.name.endswith('.zip'):
        with zipfile.ZipFile(archive) as jar:
            if len(jar.infolist()) > MAX_FILES:
                raise ValueError('JDK ZIP exceeds entry limit')
            for entry in jar.infolist():
                mode = entry.external_attr >> 16
                if (entry.flag_bits & 1 or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                        or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                    raise ValueError('JDK ZIP contains links, special files or unsupported encoding')
                if entry.is_dir():
                    copy(entry.orig_filename, 0, True, mode, None)
                else:
                    with jar.open(entry) as source:
                        copy(entry.orig_filename, entry.file_size, False, mode, source)
    else:
        regular, links = {}, []
        with tarfile.open(archive, 'r|gz') as tar:
            for entry in tar:
                if entry.issym():
                    name = reserve(entry.name)
                    if entry.size != 0:
                        raise ValueError('JDK TAR links must have no payload')
                    links.append((name, _tar_link_target(name, entry.linkname)))
                elif entry.isdir():
                    copy(entry.name, 0, True, entry.mode, None)
                elif entry.isfile():
                    with tar.extractfile(entry) as source:
                        copy(entry.name, entry.size, False, entry.mode, source)
                    regular[_relative(entry.name)] = (entry.size, entry.mode)
                else:
                    raise ValueError('JDK TAR hardlinks and special files are unsupported')
        # Only original regular members qualify, so link chains/cycles and
        # directory links cannot influence extraction paths or escape the tree.
        for name, target in links:
            if target not in regular:
                raise ValueError('JDK TAR link must target a direct regular archive member')
            size, mode = regular[target]
            source_path = _checked_child(destination, target)
            with source_path.open('rb') as source:
                info = os.fstat(source.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != size:
                    raise ValueError('JDK TAR link source changed during extraction')
                copy(name, size, False, mode, source, reserved=True)


class JdkStore:
    def __init__(self, root: Path):
        self.root = Path(root).expanduser().absolute()
        reject_links(self.root)
        if self.root == self.root.parent:
            raise ValueError('managed JDK store cannot be a filesystem root')

    def _open(self, create=False):
        reject_links(self.root)
        marker = self.root / 'store.json'
        if not self.root.exists() and not create:
            return False
        with file_lock(self.root / 'store.lock', timeout=35):
            if marker.exists():
                if json.loads(read_evidence_bytes(marker, 4096)) != STORE_MARKER:
                    raise ValueError('unrecognized JDK store marker')
            elif create:
                if set(p.name for p in self.root.iterdir()) - {'store.lock'}:
                    raise ValueError('refusing to adopt a nonempty directory as a managed JDK store')
                atomic_json(marker, STORE_MARKER)
            else:
                raise ValueError('directory is not a PluginMatrix managed JDK store')
        return True

    def _entry(self, ident):
        if not isinstance(ident, str) or not IDENTIFIER.fullmatch(ident):
            raise ValueError('invalid managed JDK id')
        return _checked_child(self.root, 'installations/' + ident)

    def _lock(self, ident, control=None):
        self._entry(ident)
        return file_lock(self.root / 'locks' / (ident + '.lock'), control, timeout=35)

    def _record(self, ident, *, verify=True):
        entry = self._entry(ident)
        record = json.loads(read_evidence_bytes(entry / 'receipt.json', MAX_RECEIPT))
        if not isinstance(record, dict) or record.get('schema') != 1 or record.get('id') != ident:
            raise ValueError('invalid managed JDK receipt identity')
        fields = record.get('package')
        if not isinstance(fields, dict) or set(fields) != set(JdkPackage.__dataclass_fields__):
            raise ValueError('invalid managed JDK package receipt')
        package = JdkPackage(**fields)
        package.validate()
        if package.id != ident:
            raise ValueError('managed JDK package identity mismatch')
        payload = entry / 'payload'
        home = _checked_child(payload, record.get('home'))
        executable = home / 'bin' / ('java.exe' if package.os == 'windows' else 'java')
        compiler = home / 'bin' / ('javac.exe' if package.os == 'windows' else 'javac')
        files = record.get('files')
        if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
            raise ValueError('invalid managed JDK file manifest')
        for name, evidence in files.items():
            _checked_child(payload, name)
            if (not isinstance(evidence, dict) or set(evidence) != {'sha256', 'size'}
                    or not isinstance(evidence['sha256'], str) or not re.fullmatch('[a-f0-9]{64}', evidence['sha256'])
                    or type(evidence['size']) is not int or not 0 <= evidence['size'] <= MAX_EXPANDED):
                raise ValueError('invalid JDK file manifest entry')
        if sum(v['size'] for v in files.values()) > MAX_EXPANDED:
            raise ValueError('JDK manifest exceeds expanded size bound')
        for path in (executable, compiler, home / 'release'):
            if path.relative_to(payload).as_posix() not in files:
                raise ValueError('managed JDK is missing java, javac or release metadata')
        if verify:
            actual = _tree(payload)
            if {p.relative_to(payload).as_posix() for p in actual} != set(files):
                raise ValueError('JDK cache tree differs from its receipt')
            for path in actual:
                expected = files[path.relative_to(payload).as_posix()]
                if _hash_regular(path, expected['size']) != (expected['sha256'], expected['size']):
                    raise ValueError('managed JDK file integrity mismatch')
        return {'schema': 1, 'id': ident, 'package': package.to_dict(), 'path': str(executable),
                'javac': str(compiler), 'major': package.major, 'jdk': True,
                'source': 'managed', 'store_root': str(self.root),
                'integrity': 'verified' if verify else 'not_checked', 'receipt': str(entry / 'receipt.json')}

    def install(self, package: JdkPackage, control=None):
        package.validate()
        if (package.os, package.architecture) != host_platform():
            raise ValueError('managed JDK package does not match this host platform')
        control = control or RunControl()
        control.check()
        self._open(create=True)
        with self._lock(package.id, control):
            entry = self._entry(package.id)
            if entry.exists():
                result = self._record(package.id)
                result['cached'] = True
                return result
            staging_root = _checked_child(self.root, 'staging')
            staging_root.mkdir(exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix='install-', dir=staging_root))
            archive = stage / package.filename
            try:
                control.emit('jdk_download_started', cached=False)
                digest, total = hashlib.sha256(), 0
                deadline = time.monotonic() + 600
                with open_official(package.url, DOWNLOAD_HOSTS) as response, archive.open('xb') as stream:
                    while True:
                        control.check()
                        if time.monotonic() > deadline:
                            raise ValueError('JDK download exceeded 600 seconds')
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > package.size:
                            raise ValueError('JDK download exceeds official archive size')
                        digest.update(chunk)
                        stream.write(chunk)
                if total != package.size or digest.hexdigest() != package.sha256:
                    raise ValueError('JDK archive size/SHA-256 mismatch')
                control.emit('jdk_download_completed', cached=False)
                payload = stage / 'payload'
                _extract(archive, payload, control)
                files = _tree(payload)
                suffix = '.exe' if package.os == 'windows' else ''
                homes = [p.parent for p in files if p.name == 'release'
                         and (p.parent/'bin'/('java' + suffix)).is_file()
                         and (p.parent/'bin'/('javac' + suffix)).is_file()]
                if len(homes) != 1:
                    raise ValueError('JDK archive must contain exactly one full java/javac home')
                home = homes[0]
                relative_home = _relative(home.relative_to(payload).as_posix())
                release = '\n'.join(read_evidence_bytes(home/'release', 65536).decode('utf-8').splitlines())
                version = re.search(r'(?m)^JAVA_VERSION="([^"]+)"$', release)
                declared_arch = re.search(r'(?m)^OS_ARCH="([^"]+)"$', release)
                arch_aliases = {'x64': {'amd64', 'x86_64', 'x64'}, 'aarch64': {'aarch64', 'arm64'}}
                if (not version or _major(version[1]) != package.major or not declared_arch
                        or declared_arch[1] not in arch_aliases[package.architecture]):
                    raise ValueError('JDK release metadata does not match the requested Java/platform: '
                                     f'JAVA_VERSION={version[1] if version else None}, '
                                     f'OS_ARCH={declared_arch[1] if declared_arch else None}')
                # Execute only after archive integrity and the complete extraction
                # pass. javac is required, since the shared runtime builds its probe.
                from .runtime import resolve_java
                from .external import run_external
                executable = home/'bin'/('java' + suffix)
                compiler = home/'bin'/('javac' + suffix)
                _, runtime_version = resolve_java(str(executable))
                result = run_external([str(compiler), '-version'], capture_output=True, text=True, timeout=10)
                if (_major(runtime_version) != package.major or result.returncode
                        or _major((result.stdout or '') + (result.stderr or '')) != package.major):
                    raise ValueError('downloaded java and javac do not match the requested JDK')
                manifest = {}
                for path in files:
                    control.check()
                    digest, size = _hash_regular(path)
                    manifest[path.relative_to(payload).as_posix()] = {'sha256': digest, 'size': size}
                record = {'schema': 1, 'id': package.id, 'package': asdict(package),
                          'home': relative_home, 'files': manifest}
                if len(json.dumps(record, indent=2).encode()) + 1 > MAX_RECEIPT:
                    raise ValueError('JDK receipt exceeds its size bound')
                atomic_json(stage / 'receipt.json', record)
                archive.unlink()  # The verified extracted tree is the executable cache.
                control.check()
                reject_links(entry)
                entry.parent.mkdir(exist_ok=True)
                os.replace(stage, entry)
                control.emit('jdk_installed', cached=False)
                result = self._record(package.id, verify=False)
                result['cached'] = False
                result['integrity'] = 'verified'
                return result
            finally:
                _remove_tree(self.root, stage)

    def list(self):
        if not self._open():
            return {'schema': 1, 'jdks': []}
        root = _checked_child(self.root, 'installations')
        if not root.exists():
            return {'schema': 1, 'jdks': []}
        entries = list(root.iterdir())
        if len(entries) > 256:
            raise ValueError('managed JDK store exceeds 256 installations')
        records = []
        for entry in sorted(entries):
            try:
                with self._lock(entry.name):
                    record = self._record(entry.name, verify=False)
                    record['integrity'] = 'not_checked'
                    records.append(record)
            except (OSError, ValueError, TypeError) as exc:
                records.append({'id': entry.name, 'integrity': 'invalid', 'error': str(exc)})
        return {'schema': 1, 'jdks': records}

    def _leases(self, ident):
        root = _checked_child(self.root, 'leases/' + ident)
        root.mkdir(parents=True, exist_ok=True)
        leases = list(root.iterdir())
        if len(leases) > 256:
            raise ValueError('too many managed JDK leases')
        return root, leases

    def _prune_leases(self, ident, *, require_idle):
        root, leases = self._leases(ident)
        for path in leases:
            if not re.fullmatch('[a-f0-9]{32}[.]lock', path.name):
                raise ValueError('unknown file in JDK lease directory')
            try:
                with file_lock(path, timeout=0):
                    pass
                path.unlink()
            except TimeoutError as exc:
                if require_idle:
                    raise ValueError('managed JDK is in use; deletion is refused') from exc
        return root

    @contextmanager
    def lease(self, ident, control=None):
        if not self._open():
            raise ValueError('managed JDK is not installed; install explicitly first')
        with ExitStack() as stack:
            with self._lock(ident, control):
                record = self._record(ident)
                package = record['package']
                if (package['os'], package['architecture']) != host_platform():
                    raise ValueError('cached JDK platform does not match this host')
                root = self._prune_leases(ident, require_idle=False)
                token = root / (uuid.uuid4().hex + '.lock')
                stack.enter_context(file_lock(token, control, timeout=0))
            try:
                yield record
            finally:
                stack.close()
                with self._lock(ident):
                    token.unlink(missing_ok=True)

    def delete(self, ident):
        if not self._open():
            raise ValueError('managed JDK store does not exist')
        with self._lock(ident):
            entry = self._entry(ident)
            # Corrupt executable bytes may be deleted, but unrelated directories
            # cannot be adopted through a missing/mismatched receipt.
            self._record(ident, verify=False)
            self._prune_leases(ident, require_idle=True)
            _remove_tree(self.root, entry)
        return {'schema': 1, 'id': ident, 'deleted': True}


def _major(value):
    match = re.search(r'(?<![\d.])(?:1\.)?(\d+)(?:[.]\d+)*', value)
    return int(match[1]) if match else None


@contextmanager
def java_selection(java: str, root: Path, control=None):
    """Keep a managed runtime leased through validation, JVM cleanup and report save."""
    ident = managed_reference(java, root)
    if ident:
        with ExitStack() as stack:
            try:
                record = stack.enter_context(JdkStore(root).lease(ident, control))
                if not java.startswith('managed:') and Path(java).expanduser().resolve() != Path(record['path']).resolve():
                    raise ValueError('managed path must select the recorded java executable')
            except (OSError, ValueError) as exc:
                raise JdkSelectionError(str(exc)) from exc
            yield record['path'], record
    else:
        yield java, None


def managed_reference(java: str, root: Path) -> str | None:
    """Recognize both opaque references and explicit paths in the selected store."""
    if not isinstance(java, str):
        raise ValueError('java must be an executable string or managed reference')
    if java.startswith('managed:'):
        ident = java[len('managed:'):]
        if not IDENTIFIER.fullmatch(ident):
            raise JdkSelectionError('invalid managed JDK id')
        return ident
    candidate, resolved = Path(java).expanduser().absolute(), Path(root).expanduser().absolute()
    if candidate.resolve().is_relative_to(resolved.resolve()):
        parts = candidate.resolve().relative_to(resolved.resolve()).parts
        if len(parts) < 4 or parts[0] != 'installations' or not IDENTIFIER.fullmatch(parts[1]) or parts[2] != 'payload':
            raise JdkSelectionError('Java path is not a published managed JDK executable')
        return parts[1]
    return None


def selection_failure(error, behavior=None):
    """Shared prerequisite outcome, before any Runtime/Behavior window exists."""
    from .behavior import initial_behavior, parse_behavior
    from .model import VerificationResult
    cancelled = isinstance(error, RunCancelled)
    result = VerificationResult(result='CANCELLED' if cancelled else 'ENVIRONMENT_INVALID',
                                failure_stage='cancelled' if cancelled else 'environment',
                                reason='cancelled before launch' if cancelled else f'managed JDK selection failed: {error}')
    result.behavior = initial_behavior(parse_behavior(behavior), result.reason)
    return result


def validate_store_separation(root: Path, outputs, inputs=()):
    reject_links(root)
    resolved = root.resolve()
    for other in [*outputs, *inputs]:
        other = Path(other).resolve()
        if other == resolved or other in resolved.parents or resolved in other.parents:
            raise ValueError('managed JDK store must be separate from verification inputs and outputs')
