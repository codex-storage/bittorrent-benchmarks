from threading import Semaphore
from typing import Iterable

import pytest

from benchmarks.core.concurrency import pflatmap


def test_should_run_iterators_in_separate_threads():
    sema = Semaphore(0)

    def task() -> Iterable[int]:
        assert sema.acquire(timeout=10)
        yield from range(10)

    it = pflatmap([task(), task()], workers=2)

    sema.release()
    for i in range(10):
        assert next(it) == i

    sema.release()
    for i in range(10):
        assert next(it) == i

    with pytest.raises(StopIteration):
        next(it)


def test_should_raise_exceptions_raised_by_tasks_at_the_end():
    def task() -> Iterable[int]:
        yield from range(10)

    def faulty_task():
        yield "yay"
        raise ValueError("I'm very faulty")

    reference_vals = set(list(range(10)) + ["yay"])
    actual_vals = set()

    it = pflatmap([task(), faulty_task()], workers=2)

    try:
        for val in it:
            actual_vals.add(val)
        assert False, "ValueError was not raised"
    except ValueError:
        pass

    assert actual_vals == reference_vals
