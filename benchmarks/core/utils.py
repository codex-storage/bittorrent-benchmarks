import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, Tuple

from typing_extensions import Generic

from benchmarks.core.network import TInitialMetadata

# A Sampler samples without replacement from [0, ..., n].
type Sampler = Callable[[int], Iterator[int]]


@dataclass
class DataHandle(Generic[TInitialMetadata], ABC):
    """A :class:`DataHandle` knows how to clean up data and metadata that has been generated
    by a :class:`DataGenerator`."""
    meta: TInitialMetadata
    data: Path

    def cleanup(self):
        if self.data.exists():
            self.data.unlink()


class DataGenerator(Generic[TInitialMetadata], ABC):
    """A :class:`DataGenerator` knows how to generate data for an :class:`Experiment`."""

    @abstractmethod
    def generate(self) -> DataHandle[TInitialMetadata]:
        """Generates fresh data and metadata and returns a :class:`DataHandle`."""
        pass


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
