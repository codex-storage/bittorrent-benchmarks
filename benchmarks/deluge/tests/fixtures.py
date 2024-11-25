from pathlib import Path
from typing import Generator

import pytest
from urllib3.util import Url, parse_url

from benchmarks.core import utils
from benchmarks.core.utils import megabytes
from benchmarks.deluge.deluge_node import DelugeNode
from benchmarks.tests.utils import shared_volume


def deluge_node(name: str, port: int) -> Generator[DelugeNode, None, None]:
    node = DelugeNode(name, volume=shared_volume(), daemon_port=port)
    node.wipe_all_torrents()
    try:
        yield node
    finally:
        node.wipe_all_torrents()


@pytest.fixture
def deluge_node1() -> Generator[DelugeNode, None, None]:
    yield from deluge_node('deluge-1', 6890)


@pytest.fixture
def deluge_node2() -> Generator[DelugeNode, None, None]:
    yield from deluge_node('deluge-2', 6893)


@pytest.fixture
def deluge_node3() -> Generator[DelugeNode, None, None]:
    yield from deluge_node('deluge-3', 6896)


@pytest.fixture
def temp_random_file() -> Generator[Path, None, None]:
    with utils.temp_random_file(size=megabytes(1)) as random_file:
        yield random_file


@pytest.fixture
def tracker() -> Url:
    return parse_url('http://127.0.0.1:8000/announce')
