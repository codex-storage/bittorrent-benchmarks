from pathlib import Path
from typing import Generator

import pytest
from urllib3.util import Url

from benchmarks.core.deluge import DelugeNode, DelugeMeta
from benchmarks.core.utils import megabytes
from benchmarks.tests.utils import shared_volume


@pytest.fixture
def deluge_node1() -> Generator[DelugeNode, None, None]:
    node = DelugeNode('deluge-1', volume=shared_volume(), daemon_port=6890)
    node.wipe_all_torrents()
    try:
        yield node
    finally:
        node.wipe_all_torrents()


def test_should_seed_files(deluge_node1: DelugeNode, temp_random_file: Path, tracker: Url):
    assert not deluge_node1.torrent_info(name='dataset1')

    deluge_node1.seed(temp_random_file, DelugeMeta(name='dataset1', announce_url=tracker))
    response = deluge_node1.torrent_info(name='dataset1')
    assert len(response) == 1
    info = response[0]

    assert info[b'name'] == b'dataset1'
    assert info[b'total_size'] == megabytes(1)
    assert info[b'is_seed'] == True
