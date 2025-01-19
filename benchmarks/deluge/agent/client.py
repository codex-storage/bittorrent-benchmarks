import requests
from tenacity import stop_after_attempt, wait_exponential, retry
from torrentool.torrent import Torrent
from urllib3.util import Url


class DelugeAgentClient:
    def __init__(self, url: Url):
        self.url = url

    def generate(self, size: int, seed: int, name: str) -> Torrent:
        @retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=4, max=16),
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
