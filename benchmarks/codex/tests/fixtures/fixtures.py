from typing import Iterator

from urllib3.util import parse_url

from benchmarks.codex.agent.codex_agent_client import CodexAgentClient
from benchmarks.codex.codex_node import CodexNode
from benchmarks.core.concurrency import await_predicate

import pytest


def codex_node(codex_api_url: str, agent_url: str) -> Iterator[CodexNode]:
    node = CodexNode(
        codex_api_url=parse_url(codex_api_url),
        agent=CodexAgentClient(parse_url(agent_url)),
    )
    assert await_predicate(node.is_ready, timeout=10, polling_interval=0.5)

    try:
        yield node
    finally:
        node.wipe_all_datasets()


@pytest.fixture
def codex_node1(codex_node_1_url: str, codex_agent_1_url: str) -> Iterator[CodexNode]:
    yield from codex_node(codex_node_1_url, codex_agent_1_url)


@pytest.fixture
def codex_node2(codex_node_2_url: str, codex_agent_2_url: str) -> Iterator[CodexNode]:
    yield from codex_node(codex_node_2_url, codex_agent_2_url)


@pytest.fixture
def codex_node3(codex_node_3_url: str, codex_agent_3_url: str) -> Iterator[CodexNode]:
    yield from codex_node(codex_node_3_url, codex_agent_3_url)
