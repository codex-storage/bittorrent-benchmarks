import random
from pathlib import Path
from typing import Callable, Iterator

# A Sampler samples without replacement from [0, ..., n].
Sampler = Callable[[int], Iterator[int]]

# A DataGenerator generates files for experiments.
DataGenerator = Callable[[], Path]


def sample(n: int) -> Iterator[int]:
    """Samples without replacement using a Fisher-Yates shuffle."""
    p = list(range(0, n))
    for i in range(n - 1):
        j = i + random.randint(0, n - i)
        tmp = p[j]
        p[j], p[j + 1] = p[j + 1], tmp
        yield p[i]
