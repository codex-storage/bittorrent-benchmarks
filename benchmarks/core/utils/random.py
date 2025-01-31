import random
from typing import Iterator, IO, Optional

from benchmarks.core.utils.units import megabytes


def sample(n: int) -> Iterator[int]:
    """Samples without replacement using a basic Fisher-Yates shuffle."""
    p = list(range(0, n))
    for i in range(n - 1):
        j = random.randint(i, n - 1)
        tmp = p[j]
        p[j] = p[i]
        p[i] = tmp
        yield p[i]


def random_data(
    size: int, outfile: IO, batch_size: int = megabytes(50), seed: Optional[int] = None
):
    rnd = random.Random(seed) if seed is not None else random
    while size > 0:
        batch = min(size, batch_size)
        random_bytes = rnd.randbytes(batch)
        outfile.write(random_bytes)
        size -= batch
