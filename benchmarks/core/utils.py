import random
from time import time, sleep
from typing import Iterator, Optional, Callable, IO


def await_predicate(
    predicate: Callable[[], bool], timeout: float = 0, polling_interval: float = 0
) -> bool:
    start_time = time()
    while (timeout == 0) or ((time() - start_time) <= timeout):
        if predicate():
            return True
        sleep(polling_interval)

    return False


def sample(n: int) -> Iterator[int]:
    """Samples without replacement using a basic Fisher-Yates shuffle."""
    p = list(range(0, n))
    for i in range(n - 1):
        j = random.randint(i, n - 1)
        tmp = p[j]
        p[j] = p[i]
        p[i] = tmp
        yield p[i]


def kilobytes(n: int) -> int:
    return n * 1024


def megabytes(n: int) -> int:
    return kilobytes(n) * 1024


def random_data(
    size: int, outfile: IO, batch_size: int = megabytes(50), seed: Optional[int] = None
):
    rnd = random.Random(seed) if seed is not None else random
    while size > 0:
        batch = min(size, batch_size)
        random_bytes = rnd.randbytes(batch)
        outfile.write(random_bytes)
        size -= batch
