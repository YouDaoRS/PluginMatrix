"""Backward-compatible Paper helpers; provider differences live in providers.py."""
from pathlib import Path

from .artifacts import ProviderError, USER_AGENT, ensure_download
from .providers import FILL_HOSTS, ServerSpec, get_provider

PaperDownloadError = ProviderError
PAPER_API = 'https://fill.papermc.io/v3/projects/paper/versions/{version}/builds'


def resolve_paper(version: str, build_id: int | None = None) -> dict:
    info = get_provider('paper').resolve(ServerSpec('paper', version, build_id))
    return {**info, 'paper_build': info['resolved_build'], 'paper_channel': info['channel'],
            'paper_time': info['build_time'], 'paper_jar_name': info['jar_name'],
            'paper_sha256': info['checksum'], 'paper_download_url': info['download_url']}


def ensure_paper(version: str, cache_dir: Path, build_id: int | None = None,
                 control=None, environment_index=None) -> tuple[Path, dict]:
    info = resolve_paper(version, build_id)
    # Preserve the original Paper cache layout and report fields.
    jar, digest = ensure_download(cache_dir, info.get('paper_jar_name'), info.get('paper_download_url'),
                                 'sha256', info.get('paper_sha256'), FILL_HOSTS, control, environment_index)
    info.update(paper_jar=str(jar.resolve()), paper_jar_sha256=digest, jar=str(jar.resolve()), jar_sha256=digest)
    return jar, info
