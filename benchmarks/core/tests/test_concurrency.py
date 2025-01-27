from concurrent.futures.thread import ThreadPoolExecutor
from threading import Semaphore
from typing import Iterable

import pytest

from benchmarks.core.concurrency import pflatmap, ensure_successful


@pytest.fixture
def executor():
    executor = None
    try:
        executor = ThreadPoolExecutor(max_workers=3)
        yield executor
    finally:
        if executor is not None:
            executor.shutdown(wait=True)


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
    except* ValueError:
        pass

    assert actual_vals == reference_vals


def test_should_return_results_when_no_failures_occur(executor):
    def reliable_task(i: int) -> int:
        return i

    assert set(
        ensure_successful(executor.submit(reliable_task, i) for i in range(10))
    ) == set(range(10))


def test_should_raise_exception_when_one_task_fails(executor):
    def reliable_task(i: int) -> int:
        return i

    def faulty_task(i: int):
        raise ValueError("I'm very faulty")

    try:
        ensure_successful(
            executor.submit(reliable_task if i % 2 == 0 else faulty_task, i)
            for i in range(10)
        )
    except* ValueError as e:
        assert len(e.exceptions) == 5
        for exception in e.exceptions:
            assert str(exception) == "I'm very faulty"
