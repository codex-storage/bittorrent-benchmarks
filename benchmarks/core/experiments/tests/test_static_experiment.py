from dataclasses import dataclass
from io import StringIO
from typing import Optional, List
from unittest.mock import patch

from benchmarks.core.experiments.static_experiment import StaticDisseminationExperiment
from benchmarks.core.network import Node, DownloadHandle
from benchmarks.logging.logging import LogParser, RequestEvent, RequestEventType


@dataclass
class MockGenData:
    size: int
    seed: int
    name: str

    def __str__(self):
        return self.name


class MockNode(Node[MockGenData, str]):
    def __init__(self, name="mock_node") -> None:
        self._name = name
        self.seeding: Optional[MockGenData] = None
        self.leeching: Optional[MockGenData] = None
        self.download_was_awaited = False
        self.cleanup_was_called = False

    @property
    def name(self) -> str:
        return self._name

    def genseed(self, size: int, seed: int, meta: str) -> MockGenData:
        self.seeding = MockGenData(size=size, seed=seed, name=meta)
        return self.seeding

    def leech(self, handle: MockGenData):
        self.leeching = handle
        return MockDownloadHandle(self)

    def remove(self, handle: MockGenData):
        if self.leeching is not None:
            assert self.leeching == handle
        elif self.seeding is not None:
            assert self.seeding == handle
        else:
            raise Exception(
                "Either leech or seed must be called before attempting a remove"
            )

        self.remove_was_called = True


class MockDownloadHandle(DownloadHandle):
    def __init__(self, parent: MockNode) -> None:
        self.parent = parent

    def await_for_completion(self, timeout: float = 0) -> bool:
        self.parent.download_was_awaited = True
        return True


def mock_network(n: int) -> List[MockNode]:
    return [MockNode(f"node-{i}") for i in range(n)]


def test_should_generate_correct_data_and_seed():
    network = mock_network(n=13)
    gendata = MockGenData(size=1000, seed=12, name="dataset1")
    seeders = [9, 6, 3]

    experiment = StaticDisseminationExperiment(
        seeders=seeders, network=network, meta="dataset1", file_size=1000, seed=12
    )

    experiment.run()

    actual_seeders = set()
    for index, node in enumerate(network):
        if node.seeding is not None:
            actual_seeders.add(index)
            assert node.seeding == gendata

    assert actual_seeders == set(seeders)


def test_should_download_at_remaining_nodes():
    network = mock_network(n=13)
    gendata = MockGenData(size=1000, seed=12, name="dataset1")
    seeders = [9, 6, 3]

    experiment = StaticDisseminationExperiment(
        seeders=seeders,
        network=network,
        meta="dataset1",
        file_size=1000,
        seed=12,
    )

    experiment.run()

    actual_leechers = set()
    for index, node in enumerate(network):
        if node.leeching is not None:
            assert node.leeching == gendata
            assert node.seeding is None
            assert node.download_was_awaited
            actual_leechers.add(index)

    assert actual_leechers == set(range(13)) - set(seeders)


def test_should_log_requests_to_seeders_and_leechers(mock_logger):
    logger, output = mock_logger
    with patch("benchmarks.core.experiments.static_experiment.logger", logger):
        network = mock_network(n=3)
        seeders = [1]

        experiment = StaticDisseminationExperiment(
            seeders=seeders,
            network=network,
            meta="dataset-1",
            file_size=1000,
            seed=12,
        )

        experiment.run()

    parser = LogParser()
    parser.register(RequestEvent)

    events = list(parser.parse(StringIO(output.getvalue())))

    assert events == [
        RequestEvent(
            destination="node-1",
            node="runner",
            name="genseed",
            request_id="dataset-1",
            type=RequestEventType.start,
            timestamp=events[0].timestamp,
        ),
        RequestEvent(
            destination="node-1",
            node="runner",
            name="genseed",
            request_id="dataset-1",
            type=RequestEventType.end,
            timestamp=events[1].timestamp,
        ),
        RequestEvent(
            destination="node-0",
            node="runner",
            name="leech",
            request_id="dataset-1",
            type=RequestEventType.start,
            timestamp=events[2].timestamp,
        ),
        RequestEvent(
            destination="node-0",
            node="runner",
            name="leech",
            request_id="dataset-1",
            type=RequestEventType.end,
            timestamp=events[3].timestamp,
        ),
        RequestEvent(
            destination="node-2",
            node="runner",
            name="leech",
            request_id="dataset-1",
            type=RequestEventType.start,
            timestamp=events[4].timestamp,
        ),
        RequestEvent(
            destination="node-2",
            node="runner",
            name="leech",
            request_id="dataset-1",
            type=RequestEventType.end,
            timestamp=events[5].timestamp,
        ),
    ]


def test_should_delete_file_from_nodes_at_the_end_of_the_experiment():
    network = mock_network(n=2)
    seeders = [1]

    experiment = StaticDisseminationExperiment(
        seeders=seeders,
        network=network,
        meta="dataset-1",
        file_size=1000,
        seed=12,
    )

    experiment.run()

    assert network[0].remove_was_called
    assert network[1].remove_was_called
