from urllib3.util import Url, parse_url
import requests
import socket

from benchmarks.codex.agent.agent import DownloadStatus
from benchmarks.core.experiments.experiments import ExperimentComponent

from benchmarks.codex.client.common import Cid


class CodexAgentClient(ExperimentComponent):
    def __init__(self, url: Url):
        self.url = url

    def is_ready(self) -> bool:
        try:
            requests.get(str(self.url._replace(path="/api/v1/hello")))
            return True
        except (ConnectionError, socket.gaierror):
            return False

    def generate(self, size: int, seed: int, name: str) -> Cid:
        response = requests.post(
            url=self.url._replace(path="/api/v1/codex/dataset").url,
            params={
                "size": str(size),
                "seed": str(seed),
                "name": name,
            },
        )

        response.raise_for_status()

        return response.text

    def download(self, cid: str) -> Url:
        response = requests.post(
            url=self.url._replace(path="/api/v1/codex/download").url,
            params={
                "cid": cid,
            },
        )

        response.raise_for_status()

        return parse_url(response.json()["status"])

    def download_status(self, cid: str) -> DownloadStatus:
        response = requests.get(
            url=self.url._replace(path=f"/api/v1/codex/download/{cid}/status").url,
        )

        response.raise_for_status()

        return DownloadStatus.model_validate_json(response.json()["status"])

    def node_id(self) -> str:
        response = requests.get(
            url=self.url._replace(path="/api/v1/codex/download/node-id").url,
        )

        response.raise_for_status()

        return response.text
