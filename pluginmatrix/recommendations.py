"""Evidence-bearing recommendations. Unknown does not become a guessed default."""
from __future__ import annotations

import re
import math
import time

POLICY_REVISION = 1
JAVA_SOURCE = 'https://docs.papermc.io/paper/getting-started/'


def _version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+(?:\.\d+)?', value):
        return None
    parts = tuple(int(p) for p in value.split('.'))
    return parts + (0,) * (3 - len(parts))


def java_baseline(version: str) -> int | None:
    """Conservative documented policy bounds, not a formula for future releases."""
    value = _version(version)
    if value is None:
        return None
    for low, high, major in (
        ((1, 8, 0), (1, 11, 2), 8),
        ((1, 12, 0), (1, 16, 4), 11),
        ((1, 16, 5), (1, 16, 5), 16),
        ((1, 17, 0), (1, 20, 4), 17),
        ((1, 20, 5), (1, 21, 4), 21),
        ((26, 1, 0), (26, 1, 0), 25),
    ):
        if low <= value <= high:
            return major
    return None


def recommend_environment(analysis: dict, *, minecraft=None, provider=None,
                          catalog=None, java_runtimes=(), build=None) -> dict:
    metadata = analysis.get('plugin')
    reasons, unresolved, conflicts = [], [], []
    if not metadata:
        unresolved.append('Plugin metadata is unavailable; correct static preflight errors first.')
        metadata = {}
    if provider is None:
        provider = 'paper'
        reasons.append({'code': 'DEFAULT_BASELINE', 'source': 'PluginMatrix profile policy',
                        'reason': 'Paper is the baseline verification target; this does not establish plugin compatibility.'})
    if provider not in ('paper', 'purpur', 'folia', 'local'):
        raise ValueError('unknown Provider')
    if provider == 'folia' and metadata.get('folia_supported') is not True:
        conflicts.append('Folia requires folia-supported: true on the target.')
    for dependency in analysis.get('dependencies', []):
        if provider == 'folia' and dependency.get('folia_supported') is not True:
            conflicts.append(f'{dependency["plugin_name"]} has no Folia support declaration.')
    if provider == 'local':
        unresolved.append('Local server runtime contract, JAR and Java requirement must be supplied explicitly.')
    if minecraft is None:
        unresolved.append('Choose the Minecraft version you intend to use; api-version does not identify this target.')
    elif _version(minecraft) is None:
        raise ValueError('invalid Minecraft version')
    else:
        reasons.append({'code': 'USER_TARGET', 'source': 'user selection', 'value': minecraft,
                        'reason': 'The selected Minecraft version is the verification target.'})
        api = metadata.get('api_version')
        if api and _version(api):
            reasons.append({'code': 'DECLARED_MINIMUM_API', 'source': metadata.get('plugin_descriptor'),
                            'value': api, 'reason': 'Minimum API declaration only; higher versions remain unverified.'})
            if _version(minecraft) < _version(api):
                conflicts.append(f'Minecraft {minecraft} is below declared api-version {api}.')
    selected_build = None
    if provider != 'local' and minecraft:
        fetched = catalog.get('fetched_at') if isinstance(catalog, dict) else None
        fresh = (type(fetched) in (int, float) and math.isfinite(fetched)
                 and -60 <= time.time() - fetched <= 6 * 60 * 60)
        if (not isinstance(catalog, dict) or not catalog.get('available')
                or catalog.get('provider') != provider or catalog.get('minecraft_version') != minecraft
                or catalog.get('source') not in ('network', 'cache') or not fresh):
            unresolved.append('A fresh official build catalog for this Provider and Minecraft version is required.')
        else:
            candidate = build if build is not None else catalog.get('recommended_build')
            builds = catalog.get('builds', [])
            if not isinstance(builds, list):
                builds = []
            entry = next((b for b in builds if isinstance(b, dict) and b.get('id') == candidate), None)
            if type(candidate) is not int or not entry:
                unresolved.append('The requested/recommended build is not confirmed by the official catalog.')
            elif build is None and provider != 'purpur' and entry.get('channel') != 'STABLE':
                unresolved.append('Only non-stable builds are available; choose a build explicitly after review.')
            else:
                selected_build = candidate
                reasons.append({'code': 'OFFICIAL_BUILD', 'source': catalog['source'],
                                'fetched_at': catalog.get('fetched_at'), 'build': candidate,
                                'channel': entry.get('channel'),
                                'reason': 'Exact published build; runtime records download provenance and checksum.'})
    major = java_baseline(minecraft) if minecraft and provider != 'local' else None
    selected_java = None
    selected_store = None
    if major is None:
        unresolved.append('No reviewed Java baseline for this target; choose and validate a JDK explicitly.')
    else:
        reasons.append({'code': 'JAVA_BASELINE', 'source': JAVA_SOURCE, 'policy_revision': POLICY_REVISION,
                        'value': major, 'reason': 'Documented server Java baseline; a matching javac is required.'})
        observed = [m.get('bytecode', {}).get('max_base_java') for m in [metadata, *analysis.get('dependencies', [])]]
        highest = max((n for n in observed if type(n) is int), default=None)
        if highest and highest > major:
            unresolved.append(f'Observed base bytecode targets Java {highest}, above the server baseline {major}; '
                              'do not assume that upgrading Java makes this server/plugin combination valid.')
        else:
            candidates = [r for r in java_runtimes if isinstance(r, dict) and r.get('major') == major
                          and r.get('jdk') is True and isinstance(r.get('javac'), str) and r['javac']
                          and isinstance(r.get('path'), str) and r['path']
                          and (r.get('source') != 'managed' or r.get('integrity') == 'verified')]
            if candidates:
                candidate = sorted(candidates, key=lambda r: r['path'].casefold())[0]
                selected_java = candidate['path']
                if candidate.get('source') == 'managed':
                    from .jdks import IDENTIFIER
                    if not isinstance(candidate.get('id'), str) or not IDENTIFIER.fullmatch(candidate['id']) or not candidate.get('store_root'):
                        raise ValueError('managed runtime recommendation lacks its store identity')
                    selected_java, selected_store = 'managed:' + candidate['id'], candidate['store_root']
                reasons.append({'code': 'MATCHING_JDK', 'source': 'local java/javac inspection',
                                'value': selected_java, 'reason': 'Observed matching Java and compiler major versions.'})
            else:
                unresolved.append(f'No validated local JDK {major}; explicitly install/select one or request a managed download.')
    if not analysis.get('valid'):
        conflicts.append('Static analysis or the local dependency graph has unresolved errors.')
    return {'schema': 1, 'policy_revision': POLICY_REVISION,
            'ready': not unresolved and not conflicts,
            'selection': {'provider': provider, 'minecraft': minecraft, 'build': selected_build, 'java': selected_java,
                          'jdk_dir': selected_store},
            'java_major': major, 'reasons': reasons, 'unresolved': unresolved, 'conflicts': conflicts,
            'scope': 'A proposed test environment, never a compatibility verdict.'}
