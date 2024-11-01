import random
from pathlib import Path
from typing import Callable, Iterator, Tuple

# A Sampler samples without replacement from [0, ..., n].
type Sampler = Callable[[int], Iterator[int]]

# A DataGenerator generates files for experiments.
type DataGenerator[TInitialMetadata] = Callable[[], Tuple[TInitialMetadata, Path]]


def sample(n: int) -> Iterator[int]:
    """Samples without replacement using a basic Fisher-Yates shuffle."""
    p = list(range(0, n))
    for i in range(n - 1):
        j = i + random.randint(0, n - i)
        tmp = p[j]
        p[j], p[j + 1] = p[j + 1], tmp
        yield p[i]


def kilobytes(n: int) -> int:
    return n * 1024


def megabytes(n: int) -> int:
    return kilobytes(n) * 1024
