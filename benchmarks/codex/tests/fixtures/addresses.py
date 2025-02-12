import pytest
import os


@pytest.fixture
def codex_node_1_url() -> str:
    return f"http://{os.environ.get('CODEX_NODE_1', 'localhost')}:6891"


@pytest.fixture
def codex_node_2_url() -> str:
    return f"http://{os.environ.get('CODEX_NODE_2', 'localhost')}:6893"


@pytest.fixture
def codex_node_3_url() -> str:
    return f"http://{os.environ.get('CODEX_NODE_3', 'localhost')}:6895"


@pytest.fixture
def codex_agent_1_url() -> str:
    return f"http://{os.environ.get('CODEX_AGENT_1', 'localhost')}:9000"


@pytest.fixture
def codex_agent_2_url() -> str:
    return f"http://{os.environ.get('CODEX_AGENT_2', 'localhost')}:9001"


@pytest.fixture
def codex_agent_3_url() -> str:
    return f"http://{os.environ.get('CODEX_AGENT_3', 'localhost')}:9002"
