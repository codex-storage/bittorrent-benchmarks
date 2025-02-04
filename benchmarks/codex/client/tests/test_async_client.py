from io import BytesIO

import pytest
from urllib3.util import parse_url

from benchmarks.codex.client.async_client import AsyncCodexClientImpl
from benchmarks.core.utils.random import random_data
from benchmarks.core.utils.units import megabytes


@pytest.mark.codex_integration
@pytest.mark.asyncio
async def test_should_upload_file(codex_node_1_url: str):
    client = AsyncCodexClientImpl(parse_url(codex_node_1_url))

    data = BytesIO()
    random_data(megabytes(1), data)

    cid = client.upload("test.txt", "application/octet-stream", data)
    assert cid is not None


@pytest.mark.codex_integration
@pytest.mark.asyncio
async def test_should_download_file(codex_node_1_url: str):
    client = AsyncCodexClientImpl(parse_url(codex_node_1_url))

    buff = BytesIO()
    random_data(megabytes(1), buff)
    data = buff.getvalue()

    cid = await client.upload("test.txt", "application/octet-stream", BytesIO(data))
    assert cid is not None

    async with client.download(cid) as content:
        downloaded = await content.readexactly(megabytes(1))

    assert downloaded == data
