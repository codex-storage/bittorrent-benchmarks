import time
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
    def __init__(
        self,
        name="mock_node",
        download_lag: float = 0,
        should_fail_download: bool = False,
    ) -> None:
        self._name = name
        self.seeding: Optional[MockGenData] = None
        self.leeching: Optional[MockGenData] = None

        self.cleanup_was_called = False
        self.download_lag = download_lag
        self.download_completed = False
        self.download_failed = False

        self.should_fail_download = should_fail_download

    @property
    def name(self) -> str:
        return self._name

    def genseed(self, size: int, seed: int, meta: str) -> MockGenData:
        self.seeding = MockGenData(size=size, seed=seed, name=meta)
        self.download_completed = True
        return self.seeding

    def leech(self, handle: MockGenData):
        self.leeching = handle
        return MockDownloadHandle(self, self.download_lag, self.should_fail_download)

    def remove(self, handle: MockGenData):
        assert (
            self.download_completed or self.download_failed
        ), "Removing download before completion"

        if self.leeching is not None:
            assert self.leeching == handle
        elif self.seeding is not None:
            assert self.seeding == handle
        else:
            raise Exception(
                "Either leech or seed must be called before attempting a remove"
            )

        self.remove_was_called = True
        return True


class MockDownloadHandle(DownloadHandle):
    def __init__(
        self, parent: MockNode, lag: float = 0, should_fail: bool = False
    ) -> None:
        self.parent = parent
        self.lag = lag
        self.should_fail = should_fail

    @property
    def node(self):
        return self.parent

    def await_for_completion(self, timeout: float = 0) -> bool:
        if self.should_fail:
            self.parent.download_failed = True
            raise Exception("Oooops, I failed!")
        time.sleep(self.lag)
        self.parent.download_completed = True
        return True


def mock_network(
    n: int, fail: Optional[List[int]] = None, download_lag: float = 0.0
) -> List[MockNode]:
    fail_list = fail or []
    return [
        MockNode(
            f"node-{i}", should_fail_download=i in fail_list, download_lag=download_lag
        )
        for i in range(n)
    ]


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
            assert node.download_completed
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


def test_should_not_have_pending_download_operations_running_at_teardown():
    network = mock_network(n=3, fail=[1], download_lag=1)
    seeders = [0]

    experiment = StaticDisseminationExperiment(
        seeders=seeders,
        network=network,
        meta="dataset-1",
        file_size=1000,
        seed=12,
    )

    try:
        experiment.run()
    except* Exception as e:
        assert len(e.exceptions) == 1
        assert str(e.exceptions[0]) == "Oooops, I failed!"

    # Downloads should have been marked as completed even
    # though we had one exception.
    assert network[0].download_completed
    assert network[2].download_completed
