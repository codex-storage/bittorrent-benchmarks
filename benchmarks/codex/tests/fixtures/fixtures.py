from urllib3.util import parse_url

from benchmarks.codex.agent.codex_agent_client import CodexAgentClient
from benchmarks.codex.codex_node import CodexNode
from benchmarks.core.concurrency import await_predicate

import pytest


def codex_node(codex_api_url: str, agent_url: str) -> CodexNode:
    node = CodexNode(
        codex_api_url=parse_url(codex_api_url),
        agent=CodexAgentClient(parse_url(agent_url)),
    )
    assert await_predicate(node.is_ready, timeout=10, polling_interval=0.5)
    # TODO wipe datasets once have support in codex for doing so.
    return node


@pytest.fixture
def codex_node1(codex_node_1_url: str, codex_agent_1_url: str) -> CodexNode:
    return codex_node(codex_node_1_url, codex_agent_1_url)


@pytest.fixture
def codex_node2(codex_node_2_url: str, codex_agent_2_url: str) -> CodexNode:
    return codex_node(codex_node_2_url, codex_agent_2_url)
