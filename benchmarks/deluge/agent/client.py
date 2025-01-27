import socket

import requests
from requests import ConnectionError
from tenacity import stop_after_attempt, wait_exponential, retry
from torrentool.torrent import Torrent
from urllib3.util import Url

from benchmarks.core.experiments.experiments import ExperimentComponent


class DelugeAgentClient(ExperimentComponent):
    def __init__(self, url: Url):
        self.url = url

    def is_ready(self) -> bool:
        try:
            requests.get(str(self.url._replace(path="/api/v1/hello")))
            return True
        except (ConnectionError, socket.gaierror):
            return False

    def generate(self, size: int, seed: int, name: str) -> Torrent:
        @retry(
            stop=stop_after_attempt(10),
            wait=wait_exponential(exp_base=2, min=4, max=16),
        )
        def _request():
            return requests.post(
                url=self.url._replace(path="/api/v1/deluge/torrent").url,
                params={
                    "size": size,
                    "seed": seed,
                    "name": name,
                },
            )

        torrent = Torrent.from_string(_request().content)
        return torrent
