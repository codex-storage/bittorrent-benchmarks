from pathlib import Path
from typing import List

from benchmarks.core.network import TInitialMetadata
from benchmarks.core.utils import Sampler, DataGenerator, DataHandle


def mock_sampler(elements: List[int]) -> Sampler:
    return lambda _: iter(elements)


class MockGenerator(DataGenerator[TInitialMetadata]):
    def __init__(self, meta: TInitialMetadata, data: Path):
        self.cleanup_called = False
        self.meta = meta
        self.data = data

    def generate(self) -> DataHandle[TInitialMetadata]:
        return MockHandle(self.meta, self.data, self)


class MockHandle(DataHandle[TInitialMetadata]):
    def __init__(self, meta: TInitialMetadata, data: Path, parent: MockGenerator):
        self.meta = meta
        self.data = data
        self.parent = parent

    def cleanup(self):
        assert not self.parent.cleanup_called
        self.parent.cleanup_called = True
