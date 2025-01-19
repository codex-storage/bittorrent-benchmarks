from pathlib import Path
from typing import Optional

from torrentool.torrent import Torrent

from benchmarks.core.utils import random_data, megabytes


class DelugeAgent:
    def __init__(self, torrents_path: Path, batch_size: int = megabytes(50)):
        self.torrents_path = torrents_path
        self.batch_size = batch_size

    def create_torrent(self, name: str, size: int, seed: Optional[int]) -> Torrent:
        torrent_path = self.torrents_path / name
        torrent_path.mkdir(parents=True, exist_ok=False)

        file_path = torrent_path / "datafile.bin"
        with file_path.open(mode="wb") as output:
            random_data(size=size, outfile=output, seed=seed)

        torrent = Torrent.create_from(torrent_path)
        torrent.name = name

        return torrent
