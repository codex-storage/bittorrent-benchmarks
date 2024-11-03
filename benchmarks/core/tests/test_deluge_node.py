from pathlib import Path

from urllib3.util import Url

from benchmarks.core.deluge import DelugeNode, DelugeMeta
from benchmarks.core.utils import megabytes


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
