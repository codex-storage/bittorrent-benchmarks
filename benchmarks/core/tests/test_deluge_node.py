from pathlib import Path
from typing import Generator

import pytest
from urllib3.util import Url

from benchmarks.core.deluge import DelugeNode, DelugeMeta
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


def test_should_seed_files(deluge_node1: DelugeNode, temp_random_file: Path, tracker: Url):
    assert not deluge_node1.torrent_info(name='dataset1')

    deluge_node1.seed(temp_random_file, DelugeMeta(name='dataset1', announce_url=tracker))
    response = deluge_node1.torrent_info(name='dataset1')
    assert len(response) == 1
    info = response[0]

    assert info[b'name'] == b'dataset1'
    assert info[b'total_size'] == megabytes(1)
    assert info[b'is_seed'] == True


def test_should_download_files(
        deluge_node1: DelugeNode, deluge_node2: DelugeNode,
        temp_random_file: Path, tracker: Url):

    assert not deluge_node1.torrent_info(name='dataset1')
    assert not deluge_node2.torrent_info(name='dataset1')

    torrent = deluge_node1.seed(temp_random_file, DelugeMeta(name='dataset1', announce_url=tracker))
    handle = deluge_node2.leech(torrent)

    assert handle.await_for_completion(5)

    response = deluge_node2.torrent_info(name='dataset1')
    assert len(response) == 1
    info = response[0]

    assert info[b'name'] == b'dataset1'
    assert info[b'total_size'] == megabytes(1)
    assert info[b'is_seed'] == True