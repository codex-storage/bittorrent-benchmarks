import os
import random
import tempfile
from abc import ABC, abstractmethod
from contextlib import contextmanager, AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from time import time, sleep
from typing import Iterator, Tuple, ContextManager, Optional, Callable

from typing_extensions import Generic

from benchmarks.core.network import TInitialMetadata


@dataclass
class ExperimentData(Generic[TInitialMetadata], AbstractContextManager, ABC):
    """:class:`ExperimentData` provides a context for providing and wiping out
    data and metadata objects, usually within the scope of an experiment."""

    @abstractmethod
    def __enter__(self) -> Tuple[TInitialMetadata, Path]:
        """Generates new data and metadata and returns it."""
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Wipes out data and metadata."""
        pass


class RandomTempData(ExperimentData[TInitialMetadata]):
    def __init__(self, size: int, meta: TInitialMetadata):
        self.meta = meta
        self.size = size
        self._context: Optional[ContextManager[Tuple[TInitialMetadata, Path]]] = None

    def __enter__(self) -> Tuple[TInitialMetadata, Path]:
        if self._context is not None:
            raise Exception("Cannot enter context twice")

        self._context = temp_random_file(self.size, "data.bin")

        return self.meta, self._context.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._context.__exit__(exc_type, exc_val, exc_tb)


@contextmanager
def temp_random_file(size: int, name: str = "data.bin"):
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        random_file = temp_dir / name
        random_bytes = os.urandom(size)
        with random_file.open("wb") as outfile:
            outfile.write(random_bytes)

        yield random_file


def await_predicate(
    predicate: Callable[[], bool], timeout: float = 0, polling_interval: float = 0
) -> bool:
    current = time()
    while (timeout == 0) or ((time() - current) <= timeout):
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
