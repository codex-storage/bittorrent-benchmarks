from pathlib import Path
from typing import Tuple

from benchmarks.core.network import TInitialMetadata
from benchmarks.core.utils import ExperimentData


class MockExperimentData(ExperimentData[TInitialMetadata]):
    def __init__(self, meta: TInitialMetadata, data: Path):
        self.cleanup_called = False
        self.meta = meta
        self.data = data

    def __enter__(self) -> Tuple[TInitialMetadata, Path]:
        return self.meta, self.data

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_called = True
