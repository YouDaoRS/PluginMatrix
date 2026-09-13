"""Official HTTP artifacts: bounded input, host allowlists, checksums and atomic cache."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from . import __version__
from .files import atomic_json, reject_links, sha256_file
from .locking import file_lock

USER_AGENT = f'PluginMatrix/{__version__} (https://github.com/YouDaoRS/PluginMatrix)'
MAX_ARTIFACT = 512 * 1024 * 1024


class ProviderError(ValueError):
    pass


def safe_url(url: str, hosts: set[str]) -> str:
    if not isinstance(url, str) or any(ord(c) < 33 for c in url):
        raise ProviderError('invalid official download URL')
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.hostname not in hosts or parts.username or parts.password or parts.port not in (None, 443):
        raise ProviderError('official download URL is outside the permitted HTTPS hosts')
    return url


class _Redirects(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_official(url: str, hosts: set[str], timeout=30):
    safe_url(url, hosts)
    opener = urllib.request.build_opener(_Redirects(hosts))
    return opener.open(urllib.request.Request(url, headers={'User-Agent': USER_AGENT}), timeout=timeout)


def read_json(url: str, hosts: set[str]):
    try:
        with open_official(url, hosts) as response:
            data = response.read(4 * 1024 * 1024 + 1)
        if len(data) > 4 * 1024 * 1024:
            raise ValueError('API response exceeds 4 MiB')
        return json.loads(data)
    except (OSError, ValueError, RecursionError) as exc:
        raise ProviderError(f'could not query official API {url}: {exc}') from exc


def safe_name(name) -> str:
    if (not isinstance(name, str) or len(name) > 180 or not re.fullmatch(r'[A-Za-z0-9_.-]+\.jar', name)
            or re.match(r'(?i)^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', name)):
        raise ProviderError('official API returned an unsafe server JAR filename')
    return name


def ensure_download(cache: Path, name: str, url: str, algorithm: str, expected: str,
                    hosts: set[str], control=None, environment_index=None) -> tuple[Path, str]:
    safe_name(name)
    length = {'sha256': 64, 'md5': 32}.get(algorithm)
    if length is None or not isinstance(expected, str) or not re.fullmatch('[a-fA-F0-9]{' + str(length) + '}', expected):
        raise ProviderError('official API did not provide a valid artifact checksum')
    safe_url(url, hosts)
    target = cache / name
    reject_links(target)
    with file_lock(cache / (name + '.lock'), control):
        reject_links(target)
        cached = target.exists()
        if cached and (not target.is_file() or target.stat().st_size > MAX_ARTIFACT):
            raise ProviderError('cache artifact is not a bounded regular file')
        if control:
            control.emit('download_started', environment_index, cached=cached)
        temporary = None
        try:
            candidate = target
            if not cached:
                with open_official(url, hosts) as response, tempfile.NamedTemporaryFile(dir=cache, delete=False) as stream:
                    temporary = Path(stream.name)
                    total = 0
                    deadline = time.monotonic() + 180
                    while True:
                        if control:
                            control.check()
                        if time.monotonic() > deadline:
                            raise ProviderError('artifact download exceeded 180 seconds')
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > MAX_ARTIFACT:
                            raise ProviderError('server artifact exceeds 512 MiB')
                        stream.write(chunk)
                candidate = temporary
            digest = hashlib.new(algorithm)
            with candidate.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
            if digest.hexdigest().lower() != expected.lower():
                raise ProviderError('server checksum mismatch; existing cache is preserved')
            actual = sha256_file(candidate)
            receipt = cache / (name + '.sha256.json')
            reject_links(receipt)
            if receipt.exists():
                if not receipt.is_file():
                    raise ProviderError('cache SHA-256 receipt must be a regular file')
                if receipt.stat().st_size > 4096:
                    raise ProviderError('cache SHA-256 receipt exceeds size limit')
                try:
                    recorded = json.loads(receipt.read_text())
                except (OSError, ValueError) as exc:
                    raise ProviderError('cache SHA-256 receipt is invalid') from exc
                if not isinstance(recorded, dict) or recorded.get('sha256') != actual:
                    raise ProviderError('cache SHA-256 receipt conflicts with artifact')
            if not cached:
                reject_links(target)
                os.replace(temporary, target)
            atomic_json(receipt, {'sha256': actual})
            if control:
                control.emit('download_completed', environment_index, cached=cached)
            return target, actual
        except OSError as exc:
            raise ProviderError(f'official artifact download/cache failure: {exc}') from exc
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
