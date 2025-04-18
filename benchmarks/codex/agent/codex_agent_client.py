"""A simple client for interacting with the Codex Agent API."""

import socket

import requests
from requests.exceptions import ConnectionError
from urllib3.util import Url, parse_url

from benchmarks.codex.client.async_client import DownloadStatus
from benchmarks.codex.client.common import Manifest
from benchmarks.core.experiments.experiments import ExperimentComponent


class CodexAgentClient(ExperimentComponent):
    def __init__(self, url: Url):
        self.url = url

    def is_ready(self) -> bool:
        try:
            requests.get(str(self.url._replace(path="/api/v1/hello")))
            return True
        except (ConnectionError, socket.gaierror):
            return False

    def generate(self, size: int, seed: int, name: str) -> Manifest:
        response = requests.post(
            url=self.url._replace(path="/api/v1/codex/dataset").url,
            params={
                "size": str(size),
                "seed": str(seed),
                "name": name,
            },
        )

        response.raise_for_status()

        return Manifest.model_validate(response.json())

    def download(self, manifest: Manifest) -> Url:
        response = requests.post(
            url=self.url._replace(path="/api/v1/codex/download").url,
            json=manifest.model_dump(mode="json"),
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

    def __str__(self):
        return f"CodexAgentClient({self.url.url})"
