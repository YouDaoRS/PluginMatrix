"""Bounded scheduling contract: ordered results, cooperative cancellation, full drain."""
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from .control import RunControl

MAX_PARALLEL = 8


def validate_parallel(value: int) -> int:
    if type(value) is not int or not 1 <= value <= MAX_PARALLEL:
        raise ValueError(f'max_parallel must be an integer from 1 to {MAX_PARALLEL}')
    return value


def schedule(items, worker, max_parallel: int, control: RunControl):
    """worker(index, item) owns cleanup in finally and returns an environment result.

    Pending work observes the same control before launching. Interrupts cancel the
    run then drain *all* workers before returning. Completed results are retained.
    """
    validate_parallel(max_parallel)
    executor = ThreadPoolExecutor(max_workers=max_parallel, thread_name_prefix='pluginmatrix')
    futures = []
    try:
        for index, item in enumerate(items):
            futures.append(executor.submit(worker, index, item))
        pending = set(futures)
        while pending:
            try:
                _, pending = wait(pending, timeout=.1, return_when=FIRST_COMPLETED)
            except KeyboardInterrupt:
                control.cancel()
        return [future.result() for future in futures]
    except BaseException:
        control.cancel()
        raise
    finally:
        # Repeated Ctrl+C never abandons processes owned by another worker.
        while True:
            try:
                executor.shutdown(wait=True)
                break
            except KeyboardInterrupt:
                control.cancel()
