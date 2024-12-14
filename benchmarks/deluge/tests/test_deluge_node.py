from pathlib import Path

import pytest

from benchmarks.core.utils import megabytes
from benchmarks.deluge.deluge_node import DelugeNode, DelugeMeta
from benchmarks.deluge.tracker import Tracker


@pytest.mark.integration
def assert_is_seed(node: DelugeNode, name: str, size: int):
    response = node.torrent_info(name=name)
    assert len(response) == 1
    info = response[0]

    assert info[b"name"] == name.encode(
        "utf-8"
    )  # not sure that this works for ANY name...
    assert info[b"total_size"] == size
    assert info[b"is_seed"]


@pytest.mark.integration
def test_should_seed_files(
    deluge_node1: DelugeNode, temp_random_file: Path, tracker: Tracker
):
    assert not deluge_node1.torrent_info(name="dataset1")

    deluge_node1.seed(
        temp_random_file, DelugeMeta(name="dataset1", announce_url=tracker.announce_url)
    )
    assert_is_seed(deluge_node1, name="dataset1", size=megabytes(1))


@pytest.mark.integration
def test_should_download_files(
    deluge_node1: DelugeNode,
    deluge_node2: DelugeNode,
    temp_random_file: Path,
    tracker: Tracker,
):
    assert not deluge_node1.torrent_info(name="dataset1")
    assert not deluge_node2.torrent_info(name="dataset1")

    torrent = deluge_node1.seed(
        temp_random_file, DelugeMeta(name="dataset1", announce_url=tracker.announce_url)
    )
    handle = deluge_node2.leech(torrent)

    assert handle.await_for_completion(5)

    assert_is_seed(deluge_node2, name="dataset1", size=megabytes(1))
