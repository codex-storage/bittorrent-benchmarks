import logging
import socket
from functools import cached_property
from typing import Iterator, Set
from urllib.error import HTTPError

import requests
from attr import dataclass
from requests.exceptions import ConnectionError
from tenacity import (
    stop_after_attempt,
    wait_exponential,
    retry,
    retry_if_not_exception_type,
)
from urllib3.util import Url

from benchmarks.codex.agent.agent import Cid, DownloadStatus
from benchmarks.codex.agent.codex_agent_client import CodexAgentClient
from benchmarks.codex.client.common import Manifest
from benchmarks.core.concurrency import await_predicate
from benchmarks.core.experiments.experiments import ExperimentComponent
from benchmarks.core.network import Node, DownloadHandle
from benchmarks.core.utils.units import megabytes

STOP_POLICY = stop_after_attempt(5)
WAIT_POLICY = wait_exponential(exp_base=2, min=4, max=16)
DELETE_TIMEOUT = 3600  # timeouts for deletes should be generous (https://github.com/codex-storage/nim-codex/pull/1103)

logger = logging.getLogger(__name__)


@dataclass
class CodexMeta:
    name: str


class CodexNode(Node[Manifest, CodexMeta], ExperimentComponent):
    def __init__(
        self,
        codex_api_url: Url,
        agent: CodexAgentClient,
        remove_data: bool = False,
    ) -> None:
        self.codex_api_url = codex_api_url
        self.agent = agent
        # Lightweight tracking of datasets created by this node. It's OK if we lose them.
        self.hosted_datasets: dict[Cid, Manifest] = {}
        self.remove_data = remove_data

    def is_ready(self) -> bool:
        try:
            requests.get(
                str(self.codex_api_url._replace(path="/api/codex/v1/debug/info"))
            )
            return True
        except (ConnectionError, socket.gaierror):
            return False

    @retry(
        stop=STOP_POLICY,
        wait=WAIT_POLICY,
        retry=retry_if_not_exception_type(HTTPError),
    )
    def genseed(self, size: int, seed: int, meta: CodexMeta) -> Manifest:
        manifest = self.agent.generate(size=size, seed=seed, name=meta.name)
        # Joins the swarm.
        self.agent.download(manifest)
        self.hosted_datasets[manifest.treeCid] = manifest
        return manifest

    @retry(
        stop=STOP_POLICY,
        wait=WAIT_POLICY,
        retry=retry_if_not_exception_type(HTTPError),
    )
    def leech(self, handle: Manifest) -> DownloadHandle:
        self.hosted_datasets[handle.treeCid] = handle
        return CodexDownloadHandle(parent=self, monitor_url=self.agent.download(handle))

    def remove(self, handle: Manifest) -> bool:
        # Removes node from the swarm.
        success = self._leave_swarm(handle)

        # Removes the data, if requested.
        if self.remove_data:
            success &= self._purge_local_data(handle)

        return success

    def swarms(self) -> Set[Cid]:
        response = requests.get(
            str(self.codex_api_url._replace(path="/api/codex/v1/download"))
        )
        response.raise_for_status()

        return set(response.json()["activeSwarms"])

    def _leave_swarm(self, handle: Manifest) -> bool:
        response = requests.delete(
            str(
                self.codex_api_url._replace(
                    path=f"/api/codex/v1/download/{handle.treeCid}"
                )
            ),
        )

        raise_if_server_error(response)

        return response.ok

    def _purge_local_data(self, handle: Manifest) -> bool:
        # Purge data on disk, if requested.
        if self.remove_data:
            response = requests.delete(
                str(
                    self.codex_api_url._replace(path=f"/api/codex/v1/data/{handle.cid}")
                ),
                timeout=DELETE_TIMEOUT,
            )

            raise_if_server_error(response)
            return response.ok

        return True

    def exists_local(self, handle: Manifest) -> bool:
        """Check if a dataset exists on the node."""
        response = requests.get(
            str(self.codex_api_url._replace(path=f"/api/codex/v1/data/{handle.cid}"))
        )

        response.close()

        if response.status_code == 404:
            return False

        if response.status_code != 200:
            response.raise_for_status()

        return True

    def download_local(
        self, handle: Manifest, chunk_size: int = megabytes(1)
    ) -> Iterator[bytes]:
        """Retrieves the contents of a locally available
        dataset from the node."""
        response = requests.get(
            str(self.codex_api_url._replace(path=f"/api/codex/v1/data/{handle.cid}"))
        )

        response.raise_for_status()

        return response.iter_content(chunk_size=chunk_size)

    def wipe_all_datasets(self):
        for dataset in list(self.hosted_datasets.values()):
            self.remove(dataset)
            del self.hosted_datasets[dataset.treeCid]

    @cached_property
    def name(self) -> str:
        return self.agent.node_id()

    def __str__(self):
        return f"CodexNode({self.codex_api_url.url, self.agent})"


class CodexDownloadHandle(DownloadHandle):
    def __init__(self, parent: CodexNode, monitor_url: Url):
        self.monitor_url = monitor_url
        self.parent = parent

    def await_for_completion(self, timeout: float = 0) -> bool:
        def _predicate():
            completion = self.completion()
            return completion.downloaded == completion.total

        return await_predicate(_predicate, timeout, polling_interval=1)

    @property
    def node(self) -> Node:
        return self.parent

    def completion(self) -> DownloadStatus:
        response = requests.get(str(self.monitor_url))
        response.raise_for_status()

        return DownloadStatus.model_validate(response.json())


def raise_if_server_error(response: requests.Response):
    """Raises an exception if the server returns a 5xx error."""
    if response.status_code >= 500 or response.status_code != 404:
        response.raise_for_status()
