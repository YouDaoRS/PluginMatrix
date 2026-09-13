"""Thread-safe cancellation and bounded, versioned application progress events."""
from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Callable


class RunCancelled(Exception):
    pass


@dataclass(frozen=True)
class ProgressEvent:
    kind: str
    environment_index: int | None = None
    data: dict = field(default_factory=dict)
    schema: int = 1
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


class RunControl:
    """One control per run. Call cancel() from any thread; callbacks must be quick.

    Callbacks are serialized and exceptions are isolated from verdict processing.
    No event history or log lines are retained here. A GUI should enqueue events.
    """
    def __init__(self, observer: Callable[[ProgressEvent], None] | None = None):
        self._cancelled = threading.Event()
        self._observer = observer
        self._lock = threading.RLock()
        self.observer_errors = 0

    def cancel(self) -> None:
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def check(self) -> None:
        if self.cancelled:
            raise RunCancelled('run cancelled')

    def emit(self, kind: str, environment_index: int | None = None, **data) -> None:
        # Only bounded implementation-owned values; never configuration, paths or logs.
        safe = {k: v for k, v in data.items() if k in {
            'total', 'completed', 'provider', 'verdict', 'elapsed', 'duration', 'max_parallel', 'cached'
        } and (type(v) in (int, float, bool) or isinstance(v, str) and len(v) <= 64)}
        with self._lock:
            if self._observer:
                try:
                    self._observer(ProgressEvent(kind, environment_index, safe))
                except Exception:
                    self.observer_errors += 1
