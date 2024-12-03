import os
from pathlib import Path
from typing import Generator

import pytest
from urllib3.util import parse_url

from benchmarks.core import utils
from benchmarks.core.utils import megabytes, await_predicate
from benchmarks.deluge.deluge_node import DelugeNode
from benchmarks.deluge.tracker import Tracker
from benchmarks.tests.utils import shared_volume


def deluge_node(name: str, address: str, port: int) -> Generator[DelugeNode, None, None]:
    node = DelugeNode(name, volume=shared_volume(), daemon_address=address, daemon_port=port)
    assert await_predicate(node.is_ready, timeout=10, polling_interval=0.5)
    node.wipe_all_torrents()
    try:
        yield node
    finally:
        node.wipe_all_torrents()


@pytest.fixture
def deluge_node1() -> Generator[DelugeNode, None, None]:
    yield from deluge_node('deluge-1', os.environ.get('DELUGE_NODE_1', 'localhost'), 6890)


@pytest.fixture
def deluge_node2() -> Generator[DelugeNode, None, None]:
    yield from deluge_node('deluge-2', os.environ.get('DELUGE_NODE_2', 'localhost'), 6893)


@pytest.fixture
def deluge_node3() -> Generator[DelugeNode, None, None]:
    yield from deluge_node('deluge-3', os.environ.get('DELUGE_NODE_3', 'localhost'), 6896)


@pytest.fixture
def temp_random_file() -> Generator[Path, None, None]:
    with utils.temp_random_file(size=megabytes(1)) as random_file:
        yield random_file


@pytest.fixture
def tracker() -> Tracker:
    return Tracker(parse_url(os.environ.get('TRACKER_ANNOUNCE_URL', 'http://127.0.0.1:8000/announce')))
