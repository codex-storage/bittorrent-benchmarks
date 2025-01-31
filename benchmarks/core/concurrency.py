import asyncio
from concurrent import futures
from concurrent.futures.thread import ThreadPoolExecutor
from queue import Queue
from time import time, sleep
from typing import Iterable, Iterator, List, cast, Awaitable, Callable

from typing_extensions import TypeVar


def await_predicate(
    predicate: Callable[[], bool], timeout: float = 0, polling_interval: float = 0
) -> bool:
    start_time = time()
    while (timeout == 0) or ((time() - start_time) <= timeout):
        if predicate():
            return True
        sleep(polling_interval)

    return False


async def await_predicate_async(
    predicate: Callable[[], Awaitable[bool]] | Callable[[], bool],
    timeout: float = 0,
    polling_interval: float = 0,
) -> bool:
    start_time = time()
    while (timeout == 0) or ((time() - start_time) <= timeout):
        if asyncio.iscoroutinefunction(predicate):
            if await predicate():
                return True
        else:
            if predicate():
                return True
        await asyncio.sleep(polling_interval)

    return False


class _End:
    pass


T = TypeVar("T")


def pflatmap(
    tasks: List[Iterable[T]], workers: int, max_queue_size: int = 0
) -> Iterator[T]:
    """
    Parallel flatmap.

    :param tasks: Iterables to be run in separate threads. Typically generators.
    :param workers: Number of workers to use.
    :param max_queue_size: Maximum size of backlogged items.

    :return: An iterator over the items produced by the tasks.
    """

    q = Queue[T | _End](max_queue_size)

    def _consume(task: Iterable[T]) -> None:
        try:
            for item in task:
                q.put(item)
        finally:
            q.put(_End())

    # TODO handle SIGTERM properly
    executor = ThreadPoolExecutor(max_workers=workers)
    try:
        task_futures = [executor.submit(_consume, task) for task in tasks]
        active_tasks = len(task_futures)

        while True:
            item = q.get()
            if isinstance(item, _End):
                active_tasks -= 1
                if active_tasks == 0:
                    break
            else:
                yield item

        # This will cause any exceptions thrown in tasks to be re-raised.
        ensure_successful(task_futures)

    finally:
        executor.shutdown(wait=True)


def ensure_successful(futs: Iterable[futures.Future[T]]) -> List[T]:
    future_list = list(futs)
    futures.wait(future_list, return_when=futures.ALL_COMPLETED)

    # We treat cancelled futures as if they were successful.
    exceptions = [
        fut.exception()
        for fut in future_list
        if not fut.cancelled() and fut.exception() is not None
    ]

    if exceptions:
        raise ExceptionGroup(
            "One or more computations failed to complete successfully",
            cast(List[Exception], exceptions),
        )

    return [cast(T, fut.result()) for fut in future_list]
