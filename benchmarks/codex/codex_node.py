import logging
import socket
from functools import cached_property
from urllib.error import HTTPError

import requests
from attr import dataclass
from tenacity import (
    stop_after_attempt,
    wait_exponential,
    retry,
    retry_if_not_exception_type,
)
from urllib3.util import Url

from benchmarks.codex.agent.agent import Cid, DownloadStatus
from benchmarks.codex.agent.codex_agent_client import CodexAgentClient
from benchmarks.core.concurrency import await_predicate
from benchmarks.core.experiments.experiments import ExperimentComponent
from benchmarks.core.network import Node, DownloadHandle

STOP_POLICY = stop_after_attempt(5)
WAIT_POLICY = wait_exponential(exp_base=2, min=4, max=16)

logger = logging.getLogger(__name__)


@dataclass
class CodexMeta:
    name: str


class CodexNode(Node[Cid, CodexMeta], ExperimentComponent):
    def __init__(self, codex_api_url: Url, agent: CodexAgentClient):
        self.codex_api_url = codex_api_url
        self.agent = agent

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
    def genseed(self, size: int, seed: int, meta: CodexMeta) -> Cid:
        return self.agent.generate(size=size, seed=seed, name=meta.name)

    @retry(
        stop=STOP_POLICY,
        wait=WAIT_POLICY,
        retry=retry_if_not_exception_type(HTTPError),
    )
    def leech(self, handle: Cid) -> DownloadHandle:
        return CodexDownloadHandle(parent=self, monitor_url=self.agent.download(handle))

    def remove(self, handle: Cid) -> bool:
        logger.warning("Removing a file from Codex is not currently supported.")
        return False

    @cached_property
    def name(self) -> str:
        return self.agent.node_id()


class CodexDownloadHandle(DownloadHandle):
    def __init__(self, parent: CodexNode, monitor_url: Url):
        self.monitor_url = monitor_url
        self.parent = parent

    def await_for_completion(self, timeout: float = 0) -> bool:
        def _predicate():
            completion = self.completion()
            return completion.downloaded == completion.total

        return await_predicate(_predicate, timeout)

    @property
    def node(self) -> Node:
        return self.parent

    def completion(self) -> DownloadStatus:
        response = requests.get(str(self.monitor_url))
        response.raise_for_status()

        return DownloadStatus.model_validate(response.json())
