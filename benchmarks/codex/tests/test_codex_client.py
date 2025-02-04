from io import BytesIO

import pytest
from urllib3.util import parse_url

from benchmarks.codex.client.async_client import AsyncCodexClientImpl
from benchmarks.core.utils.random import random_data


@pytest.fixture
def random_file() -> BytesIO:
    b = BytesIO()
    random_data(size=2048, outfile=b)
    b.seek(0)
    return b


@pytest.mark.codex_integration
@pytest.mark.asyncio
async def test_should_upload_file(codex_node_1_url: str, random_file):
    codex_client = AsyncCodexClientImpl(parse_url(codex_node_1_url))
    cid = await codex_client.upload(
        content=random_file, name="dataset-1", mime_type="application/octet-stream"
    )

    assert cid is not None

    manifest = await codex_client.manifest(cid)

    assert manifest.cid == cid
    assert manifest.datasetSize == 2048
    assert manifest.mimetype == "application/octet-stream"
