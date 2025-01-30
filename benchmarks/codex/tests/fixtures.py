import os

import pytest
from urllib3.util import parse_url

from benchmarks.codex.client import CodexClient


@pytest.fixture
def codex_client_1():
    # TODO wipe data between tests
    return CodexClient(
        parse_url(f"http://{os.environ.get('CODEX_NODE_1', 'localhost')}:8091")
    )
