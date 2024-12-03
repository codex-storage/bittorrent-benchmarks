from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple, Union

from benchmarks.core.experiments.static_experiment import StaticDisseminationExperiment
from benchmarks.core.experiments.tests.utils import MockExperimentData
from benchmarks.core.network import Node, DownloadHandle


@dataclass
class MockHandle:
    path: Path
    name: str


class MockNode(Node[MockHandle, str]):

    def __init__(self) -> None:
        self.seeding: Optional[Tuple[MockHandle, Path]] = None
        self.leeching: Optional[MockHandle] = None
        self.download_was_awaited = False

    @property
    def name(self) -> str:
        return 'mock_node'

    def seed(
            self,
            file: Path,
            handle: Union[str, MockHandle]
    ) -> MockHandle:

        if isinstance(handle, MockHandle):
            self.seeding = (handle, file)
        else:
            self.seeding = (MockHandle(name=handle, path=file), file)

        return self.seeding[0]

    def leech(self, handle: MockHandle):

        self.leeching = handle
        return MockDownloadHandle(self)


class MockDownloadHandle(DownloadHandle):
    def __init__(self, parent: MockNode) -> None:
        self.parent = parent

    def await_for_completion(self, timeout: float = 0) -> bool:
        self.parent.download_was_awaited = True
        return True


def mock_network(n: int) -> List[MockNode]:
    return [MockNode() for _ in range(n)]


def test_should_place_seeders():
    network = mock_network(n=13)
    data = MockExperimentData(meta='data', data=Path('/path/to/data'))
    seeders = [9, 6, 3]

    experiment = StaticDisseminationExperiment(
        seeders=seeders,
        network=network,
        data=data,
    )

    experiment.run()

    actual_seeders = set()
    for index, node in enumerate(network):
        if node.seeding is not None:
            actual_seeders.add(index)
            assert node.seeding[0] == MockHandle(name=data.meta, path=data.data)

    assert actual_seeders == set(seeders)


def test_should_download_at_remaining_nodes():
    network = mock_network(n=13)
    data = MockExperimentData(meta='data', data=Path('/path/to/data'))
    seeders = [9, 6, 3]

    experiment = StaticDisseminationExperiment(
        seeders=seeders,
        network=network,
        data=data,
    )

    experiment.run()

    actual_leechers = set()
    for index, node in enumerate(network):
        if node.leeching is not None:
            assert node.leeching.path == data.data
            assert node.leeching.name == data.meta
            assert node.seeding is None
            assert node.download_was_awaited
            actual_leechers.add(index)

    assert actual_leechers == set(range(13)) - set(seeders)


def test_should_delete_generated_file_at_end_of_experiment():
    network = mock_network(n=2)
    data = MockExperimentData(meta='data', data=Path('/path/to/data'))
    seeders = [1]

    experiment = StaticDisseminationExperiment(
        seeders=seeders,
        network=network,
        data=data,
    )

    experiment.run()

    assert data.cleanup_called
