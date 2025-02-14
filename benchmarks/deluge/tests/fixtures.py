import os
from typing import Generator

import pytest
from urllib3.util import parse_url

from benchmarks.core.concurrency import await_predicate
from benchmarks.deluge.agent.deluge_agent_client import DelugeAgentClient
from benchmarks.deluge.deluge_node import DelugeNode
from benchmarks.deluge.tracker import Tracker


def deluge_node(
    name: str, address: str, port: int, agent_url: str
) -> Generator[DelugeNode, None, None]:
    node = DelugeNode(
        name,
        daemon_address=address,
        daemon_port=port,
        agent=DelugeAgentClient(parse_url(agent_url)),
    )
    assert await_predicate(node.is_ready, timeout=10, polling_interval=0.5)
    node.wipe_all_torrents()
    try:
        yield node
    finally:
        node.wipe_all_torrents()


@pytest.fixture
def deluge_node1() -> Generator[DelugeNode, None, None]:
    yield from deluge_node(
        "deluge-1",
        os.environ.get("DELUGE_NODE_1", "localhost"),
        6890,
        os.environ.get("DELUGE_AGENT_1", "http://localhost:9001"),
    )


@pytest.fixture
def deluge_node2() -> Generator[DelugeNode, None, None]:
    yield from deluge_node(
        "deluge-2",
        os.environ.get("DELUGE_NODE_2", "localhost"),
        6893,
        os.environ.get("DELUGE_AGENT_2", "http://localhost:9002"),
    )


@pytest.fixture
def deluge_node3() -> Generator[DelugeNode, None, None]:
    yield from deluge_node(
        "deluge-3",
        os.environ.get("DELUGE_NODE_3", "localhost"),
        6896,
        os.environ.get("DELUGE_AGENT_3", "http://localhost:9003"),
    )


@pytest.fixture
def tracker() -> Tracker:
    return Tracker(
        parse_url(
            os.environ.get("TRACKER_ANNOUNCE_URL", "http://127.0.0.1:8000/announce")
        )
    )
