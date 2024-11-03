import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from urllib3.util import Url, parse_url

from benchmarks.core.deluge import DelugeNode
from benchmarks.core.utils import megabytes
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
def temp_random_file() -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        random_file = temp_dir / 'data.bin'
        random_bytes = os.urandom(megabytes(1))
        with random_file.open('wb') as outfile:
            outfile.write(random_bytes)

        yield random_file


@pytest.fixture
def tracker() -> Url:
    return parse_url('http://127.0.0.1:8000/announce')
