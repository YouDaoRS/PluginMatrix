"""Server Provider contract: server differences live here, verdict/processes in runtime."""
from __future__ import annotations

import json
import re
import zipfile
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from .artifacts import ProviderError, ensure_download, read_json, safe_name, safe_url
from .files import sha256_file

FILL_HOSTS = {'fill.papermc.io', 'fill-data.papermc.io'}
PURPUR_HOSTS = {'api.purpurmc.org'}
PASS_SCOPE = ('PASS confirms server readiness, matching target identity and CodeSource, enablement '
              'and fresh probe samples throughout the stability window. It does not verify all plugin features.')
FOLIA_SCOPE = ('Folia PASS only confirms acceptance, enablement and observed stability in a regionized runtime. '
               'It does not prove thread safety, cross-region safety or gameplay compatibility.')


@dataclass(frozen=True)
class ServerSpec:
    type: str
    version: str
    build: int | None = None
    jar: Path | None = None
    name: str | None = None
    runtime: str | None = None
    metadata: dict = field(default_factory=dict)
    heap_mb: int = 1024

    def to_dict(self) -> dict:
        value = asdict(self)
        value['build'] = self.build if self.build is not None else 'latest'
        if self.type == 'local':
            value.pop('build')
        if self.jar:
            value['jar'] = str(self.jar)
        return {k: v for k, v in value.items() if v is not None and v != {}}


@dataclass(frozen=True)
class ProviderMetadata:
    type: str
    name: str
    status: str
    official: bool
    regionized: bool
    capabilities: tuple[str, ...]
    config_fields: dict[str, str]
    pass_scope: str = PASS_SCOPE
    api: str | None = None


def parse_server(raw: object, base: Path = Path('.')) -> ServerSpec:
    if not isinstance(raw, dict):
        raise ProviderError('server must be an object with type and version')
    kind = raw.get('type')
    if kind == 'custom':
        kind = 'local'
    provider = get_provider(kind)
    unknown = set(raw) - set(provider.metadata.config_fields)
    if unknown:
        raise ProviderError(f'unknown {kind} server fields: {sorted(unknown)}; consult pluginmatrix providers')
    version = raw.get('version')
    if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', version.strip()):
        raise ProviderError('server.version must be a Minecraft version such as 1.21.4')
    build = raw.get('build')
    if build == 'latest':
        build = None
    if build is not None and (type(build) is not int or build <= 0):
        raise ProviderError('server.build must be a positive integer or latest')
    heap = raw.get('heap_mb', 1024)
    if type(heap) is not int or not 256 <= heap <= 32768:
        raise ProviderError('server.heap_mb must be an integer between 256 and 32768')
    jar, name, runtime = None, None, None
    extra = raw.get('metadata', {})
    if not isinstance(extra, dict) or len(json.dumps(extra, allow_nan=False)) > 16384:
        raise ProviderError('server.metadata must be a JSON object of at most 16 KiB')
    if kind == 'local':
        value, name, runtime = raw.get('jar'), raw.get('name'), raw.get('runtime')
        if not isinstance(value, str) or not value.strip():
            raise ProviderError('local server.jar requires a user-supplied JAR path')
        jar = Path(value).expanduser()
        jar = (base / jar).resolve() if not jar.is_absolute() else jar.resolve()
        if not isinstance(name, str) or not name.strip() or len(name) > 128 or any(ord(c) < 32 for c in name):
            raise ProviderError('local server.name must be an explicit nonempty display name (up to 128 characters)')
        if runtime not in ('paperclip', 'bukkit', 'folia'):
            raise ProviderError('local server.runtime must explicitly select paperclip, bukkit or folia; unknown contracts fail closed')
    return ServerSpec(kind, version.strip(), build, jar, name, runtime, extra, heap)


def resolve_fill(project: str, version: str, build_id: int | None = None) -> dict:
    url = f'https://fill.papermc.io/v3/projects/{project}/versions/{version}/builds'
    builds = read_json(url, FILL_HOSTS)
    title = project.title()
    if not isinstance(builds, list) or not builds:
        raise ProviderError(f'no {title} builds for requested version {version!r}. Expected a published version; correct server.version.')
    if any(not isinstance(b, dict) or type(b.get('id')) is not int or b['id'] <= 0
           or b.get('channel') not in ('STABLE', 'BETA', 'ALPHA', 'EXPERIMENTAL') for b in builds):
        raise ProviderError('official API returned malformed build records')
    # Fixed builds are exact, latest retains 0.5.1 stable-first fallback semantics.
    candidates = builds if build_id else [b for b in builds if b['channel'] == 'STABLE'] or builds
    if build_id:
        candidates = [b for b in candidates if b['id'] == build_id]
    if not candidates:
        raise ProviderError(f'requested {project}_build {build_id} was not found for {title} {version}. Expected an exact published build; correct it or remove it for latest.')
    chosen = max(candidates, key=lambda b: b['id'])
    try:
        download = chosen['downloads']['server:default']
        name = safe_name(download['name'])
        checksum = download['checksums']['sha256']
        if not isinstance(checksum, str) or not re.fullmatch(r'[a-fA-F0-9]{64}', checksum):
            raise ValueError('invalid SHA-256')
        source = safe_url(download['url'], FILL_HOSTS)
    except (KeyError, TypeError, ValueError) as exc:
        raise ProviderError(f'official API has invalid server:default download: {exc}') from exc
    return dict(server_type=project, server_name=title, official=True, minecraft_version=version,
                requested_build=build_id if build_id else 'latest', resolved_build=chosen['id'],
                channel=chosen['channel'], build_time=chosen.get('time'), jar_name=name,
                download_url=source, api_url=url, checksum_algorithm='sha256', checksum=checksum.lower())


def _version_key(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in value.split('.'))


def _catalog_versions(value: object, project: str) -> list[str]:
    if not isinstance(value, dict):
        raise ProviderError('official API returned malformed project metadata')
    versions = value.get('versions')
    if project == 'purpur':
        if value.get('project') != project or not isinstance(versions, list):
            raise ProviderError('Purpur API returned malformed version metadata')
        candidates = versions
    else:
        identity = value.get('project')
        if not isinstance(identity, dict) or identity.get('id') != project or not isinstance(versions, dict):
            raise ProviderError('PaperMC API returned malformed version metadata')
        candidates = [version for group in versions.values() if isinstance(group, list) for version in group]
    normalized = {version for version in candidates
                  if isinstance(version, str) and re.fullmatch(r'\d+\.\d+(?:\.\d+)?', version)}
    if not normalized:
        raise ProviderError(f'official API returned no supported {project} versions')
    return sorted(normalized, key=_version_key, reverse=True)


def _fill_catalog_builds(value: object) -> dict:
    if (not isinstance(value, list) or not value
            or any(not isinstance(item, dict) or type(item.get('id')) is not int or item['id'] <= 0
                   or item.get('channel') not in ('STABLE', 'BETA', 'ALPHA', 'EXPERIMENTAL')
                   for item in value)):
        raise ProviderError('official API returned malformed build metadata')
    builds = sorted(({'id': item['id'], 'channel': item['channel'], 'time': item.get('time')}
                     for item in value), key=lambda item: item['id'], reverse=True)
    stable = [item for item in builds if item['channel'] == 'STABLE']
    return {'builds': builds, 'recommended_build': (stable or builds)[0]['id']}


class ServerProvider:
    metadata: ProviderMetadata

    def validate(self, spec: ServerSpec) -> None:
        normalized = parse_server(spec.to_dict())
        # Windows hosted runners can expose the same temporary path through an
        # 8.3 alias (RUNNER~1) while Path.resolve() expands it (runneradmin).
        # The normalized absolute path is the provider identity; hash and
        # input-alias checks still run before any local JAR is executed.
        comparable = replace(spec, jar=normalized.jar) if spec.jar is not None else spec
        if normalized != comparable:
            raise ProviderError('server specification is not normalized')

    def requested_metadata(self, spec: ServerSpec) -> dict:
        regionized = self.metadata.regionized or spec.runtime == 'folia'
        return dict(server_type=spec.type, server_name=spec.name or self.metadata.name,
                    official=self.metadata.official, minecraft_version=spec.version,
                    requested_build=spec.build if spec.build is not None else 'latest',
                    resolved_build=None, regionized_runtime=regionized,
                    runtime_profile=spec.runtime or ('folia' if regionized else 'paperclip'),
                    pass_scope=FOLIA_SCOPE if regionized else PASS_SCOPE, provider_metadata=dict(spec.metadata))

    def resolve(self, spec: ServerSpec) -> dict:
        self.validate(spec)
        return {**self.requested_metadata(spec), **resolve_fill(spec.type, spec.version, spec.build)}

    def catalog_versions(self) -> list[str]:
        return _catalog_versions(read_json(self.metadata.api, FILL_HOSTS), self.metadata.type)

    def catalog_builds(self, version: str) -> dict:
        if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', version):
            raise ProviderError('Minecraft version must use numbers such as 1.21.4')
        url = f'https://fill.papermc.io/v3/projects/{self.metadata.type}/versions/{version}/builds'
        return _fill_catalog_builds(read_json(url, FILL_HOSTS))

    def prepare(self, spec: ServerSpec, cache: Path, control=None, environment_index=None) -> tuple[Path, dict]:
        info = self.resolve(spec)
        jar, digest = ensure_download(cache / spec.type / spec.version / str(info['resolved_build']),
                                     info['jar_name'], info['download_url'], info['checksum_algorithm'],
                                     info['checksum'], PURPUR_HOSTS if spec.type == 'purpur' else FILL_HOSTS,
                                     control, environment_index)
        return jar, {**info, 'jar': str(jar.resolve()), 'jar_sha256': digest}

    def cache_identity(self, spec: ServerSpec, info: dict) -> str:
        return f'{spec.type}-{spec.version}-{info.get("resolved_build") or "local"}-{info["jar_sha256"]}'

    def runtime_cache(self, spec: ServerSpec, info: dict, cache: Path) -> Path | None:
        if spec.type == 'local':
            return None
        return cache / 'runtime' / self.cache_identity(spec, info)

    def command(self, spec: ServerSpec, java: str, jar_name: str) -> list[str]:
        return [java, f'-Xmx{spec.heap_mb}M', '-Dterminal.jline=false', '-Dterminal.ansi=false',
                '-jar', jar_name, '--nogui']

    def allowed_sources(self, spec: ServerSpec | None, target: Path) -> tuple[Path, ...]:
        if spec and spec.type == 'local' and spec.runtime == 'bukkit':
            return (target,)
        return (target, target.parent / '.paper-remapped' / target.name)

    def interpret_server_line(self, line: str) -> set[str]:
        lowered = line.lower()
        events = set()
        if re.search(r'\bdone \([^\r\n]+\)!?', lowered):
            events.add('ready')
        if any(x in lowered for x in ('failed to bind', 'address already in use', 'server thread stopped', 'error during server startup')):
            events.add('startup_failure')
        if any(x in lowered for x in ('stopping server', 'stopping the server', 'shutting down server')):
            events.add('shutdown')
        if any(x in lowered for x in ('paperclip.setupclasspath', 'unable to access jarfile', 'could not reserve enough space')):
            events.add('environment_failure')
        if any(x in lowered for x in ('failed to download', 'could not download')) and any(
                x in lowered for x in ('mojang', 'paperclip', 'downloadcontext', 'server dependency', 'paper jar')):
            events.add('environment_failure')
        return events

    def check_plugin(self, spec: ServerSpec, metadata: dict) -> str | None:
        if (self.metadata.regionized or spec.runtime == 'folia') and metadata.get('folia_supported') is not True:
            return 'Folia requires folia-supported: true in the plugin descriptor; no thread-safety claim is inferred'
        return None


COMMON = {'type': 'Provider identifier', 'version': 'Required Minecraft version',
          'build': 'Positive integer or latest (default)', 'heap_mb': 'JVM heap limit in MiB; default 1024'}


class PaperProvider(ServerProvider):
    metadata = ProviderMetadata('paper', 'Paper', 'supported', True, False,
                                ('official_download', 'fixed_build', 'latest_build', 'paper_remap', 'bukkit_probe'),
                                COMMON, api='https://fill.papermc.io/v3/projects/paper')


class PurpurProvider(ServerProvider):
    metadata = ProviderMetadata('purpur', 'Purpur', 'supported', True, False,
                                ('official_download', 'fixed_build', 'latest_build', 'paper_remap', 'bukkit_probe'),
                                COMMON, api='https://api.purpurmc.org/v2/purpur')

    def resolve(self, spec: ServerSpec) -> dict:
        self.validate(spec)
        url = f'https://api.purpurmc.org/v2/purpur/{spec.version}/{spec.build or "latest"}'
        value = read_json(url, PURPUR_HOSTS)
        if not isinstance(value, dict) or value.get('project') != 'purpur' or value.get('version') != spec.version or value.get('result') != 'SUCCESS':
            raise ProviderError('Purpur API returned an unsuccessful or mismatched build')
        build = value.get('build')
        if not isinstance(build, str) or not re.fullmatch('[1-9][0-9]*', build) or spec.build is not None and int(build) != spec.build:
            raise ProviderError('Purpur API returned an invalid/mismatched build number')
        checksum = value.get('md5')
        if not isinstance(checksum, str) or not re.fullmatch('[a-fA-F0-9]{32}', checksum):
            raise ProviderError('Purpur API did not provide its MD5 checksum')
        return {**self.requested_metadata(spec), 'resolved_build': int(build), 'api_url': url,
                'jar_name': f'purpur-{spec.version}-{build}.jar',
                'download_url': f'https://api.purpurmc.org/v2/purpur/{spec.version}/{build}/download',
                'checksum_algorithm': 'md5', 'checksum': checksum.lower(),
                'integrity_note': 'Official Purpur API supplies MD5, not SHA-256; PluginMatrix additionally records and pins local SHA-256.'}

    def catalog_versions(self) -> list[str]:
        return _catalog_versions(read_json(self.metadata.api, PURPUR_HOSTS), self.metadata.type)

    def catalog_builds(self, version: str) -> dict:
        if not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', version):
            raise ProviderError('Minecraft version must use numbers such as 1.21.4')
        value = read_json(f'https://api.purpurmc.org/v2/purpur/{version}', PURPUR_HOSTS)
        builds = value.get('builds') if isinstance(value, dict) else None
        if (not isinstance(value, dict) or value.get('project') != 'purpur' or value.get('version') != version
                or not isinstance(builds, dict) or not isinstance(builds.get('all'), list)
                or not isinstance(builds.get('latest'), str) or not builds['latest'].isdigit()
                or any(not isinstance(item, str) or not item.isdigit() or int(item) <= 0 for item in builds['all'])):
            raise ProviderError('Purpur API returned malformed build metadata')
        normalized = sorted({int(item) for item in builds['all']}, reverse=True)
        latest = int(builds['latest'])
        if not normalized or latest not in normalized:
            raise ProviderError('Purpur API returned an inconsistent latest build')
        return {'builds': [{'id': item, 'channel': None, 'time': None} for item in normalized],
                'recommended_build': latest}


class FoliaProvider(ServerProvider):
    metadata = ProviderMetadata('folia', 'Folia', 'experimental', True, True,
                                ('official_download', 'fixed_build', 'latest_build', 'paper_remap', 'global_region_probe', 'requires_folia_declaration'),
                                COMMON, FOLIA_SCOPE, 'https://fill.papermc.io/v3/projects/folia')


class LocalProvider(ServerProvider):
    metadata = ProviderMetadata('local', 'User-supplied server', 'contract_limited', False, False,
                                ('local_jar', 'sha256', 'explicit_runtime_contract'),
                                {**{k: v for k, v in COMMON.items() if k != 'build'},
                                 'jar': 'Required local server JAR', 'name': 'Required user-declared name',
                                 'runtime': 'Required: paperclip, bukkit, or folia', 'metadata': 'Optional JSON object (16 KiB)'})

    def resolve(self, spec: ServerSpec) -> dict:
        self.validate(spec)
        jar = spec.jar
        if not jar or not jar.is_file() or jar.stat().st_size > 512 * 1024 * 1024 or not zipfile.is_zipfile(jar):
            raise ProviderError('local server JAR must be an existing ZIP/JAR of at most 512 MiB')
        return {**self.requested_metadata(spec), 'requested_build': None, 'jar': str(jar),
                'jar_name': jar.name, 'jar_sha256': sha256_file(jar), 'download_url': None,
                'version_source': 'user_declaration', 'checksum_algorithm': 'sha256'}

    def prepare(self, spec: ServerSpec, cache: Path, control=None, environment_index=None) -> tuple[Path, dict]:
        if control:
            control.check()
        return spec.jar, self.resolve(spec)

    def catalog_versions(self) -> list[str]:
        return []

    def catalog_builds(self, version: str) -> dict:
        return {'builds': [], 'recommended_build': None}


_PROVIDERS = {p.metadata.type: p for p in (PaperProvider(), PurpurProvider(), FoliaProvider(), LocalProvider())}


def get_provider(kind: str) -> ServerProvider:
    if not isinstance(kind, str) or kind not in _PROVIDERS:
        raise ProviderError(f'unsupported server.type {kind!r}; use paper, purpur, folia or local')
    return _PROVIDERS[kind]


def inspect_providers() -> list[dict]:
    return [asdict(p.metadata) for p in _PROVIDERS.values()]
