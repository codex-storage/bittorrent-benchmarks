from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple, Union, Sequence

from benchmarks.core.network import FileSharingNetwork, Node
from benchmarks.core.utils import Sampler
from benchmarks.experiments.static_experiment import StaticDisseminationExperiment


@dataclass
class MockHandle:
    path: Path
    name: str


def mock_sampler(elements: List[int]) -> Sampler:
    return lambda _: iter(elements)


class MockNode(Node[MockHandle, str]):

    def __init__(self) -> None:
        self.seeding: Optional[Tuple[MockHandle, Path]] = None
        self.leeching: Optional[MockHandle] = None

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


class MockFileSharingNetwork(FileSharingNetwork[MockHandle, str]):

    def __init__(self, n: int) -> None:
        self._nodes = [MockNode() for _ in range(n)]

    @property
    def nodes(self) -> Sequence[Node[MockHandle, str]]:
        return self._nodes


def test_should_place_seeders():
    network = MockFileSharingNetwork(n=13)
    file = Path('/path/to/data')
    seeder_indexes = [9, 6, 3]

    experiment = StaticDisseminationExperiment(
        seeders=3,
        sampler=mock_sampler(seeder_indexes),
        network=network,
        generator=lambda: ('data', Path('/path/to/data')),
    )

    experiment.run()

    actual_seeders = set()
    for index, node in enumerate(network.nodes):
        if node.seeding is not None:
            actual_seeders.add(index)
            assert node.seeding[0] == MockHandle(name='data', path=file)

    assert actual_seeders == set(seeder_indexes)


def test_should_place_leechers():
    network = MockFileSharingNetwork(n=13)
    file = Path('/path/to/data')
    seeder_indexes = [9, 6, 3]

    experiment = StaticDisseminationExperiment(
        seeders=3,
        sampler=mock_sampler(seeder_indexes),
        network=network,
        generator=lambda: ('data', Path('/path/to/data')),
    )

    experiment.run()

    actual_leechers = set()
    for index, node in enumerate(network.nodes):
        if node.leeching is not None:
            assert node.leeching.path == file
            assert node.leeching.name == 'data'
            assert node.seeding is None
            actual_leechers.add(index)

    assert actual_leechers == set(range(13)) - set(seeder_indexes)
