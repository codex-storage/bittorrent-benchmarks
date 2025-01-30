import tempfile
from pathlib import Path

import pytest
from torrentool.torrent import TorrentFile

from benchmarks.deluge.agent.agent import DelugeAgent


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.mark.deluge_integration
def test_should_create_torrent_at_specified_location(temp_dir):
    agent = DelugeAgent(
        torrents_path=temp_dir,
    )

    torrent_file = agent.create_torrent(
        name="dataset-1",
        size=1024,
        seed=12,
    )

    assert torrent_file.name == "dataset-1"
    assert torrent_file.total_size == 1024
    assert torrent_file.files == [TorrentFile("dataset-1/datafile.bin", 1024)]

    assert (temp_dir / "dataset-1" / "datafile.bin").stat().st_size == 1024


@pytest.mark.deluge_integration
def test_should_generate_identical_torrent_files_for_identical_seeds(temp_dir):
    agent1 = DelugeAgent(
        torrents_path=temp_dir / "d1",
    )

    torrent_file1 = agent1.create_torrent(
        name="dataset-1",
        size=1024,
        seed=12,
    )

    agent2 = DelugeAgent(
        torrents_path=temp_dir / "d2",
    )

    torrent_file2 = agent2.create_torrent(
        name="dataset-1",
        size=1024,
        seed=12,
    )

    assert torrent_file1.to_string() == torrent_file2.to_string()


@pytest.mark.deluge_integration
def test_should_generate_different_torrent_files_for_different_seeds(temp_dir):
    agent1 = DelugeAgent(
        torrents_path=temp_dir / "d1",
    )

    torrent_file1 = agent1.create_torrent(
        name="dataset-1",
        size=1024,
        seed=12,
    )

    agent2 = DelugeAgent(
        torrents_path=temp_dir / "d2",
    )

    torrent_file2 = agent2.create_torrent(
        name="dataset-1",
        size=1024,
        seed=13,
    )

    assert torrent_file1.to_string() != torrent_file2.to_string()
