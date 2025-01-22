from concurrent.futures.thread import ThreadPoolExecutor
from queue import Queue
from typing import Iterable, Iterator, List

from typing_extensions import TypeVar


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
        for future in task_futures:
            future.result()

    finally:
        executor.shutdown(wait=True)
