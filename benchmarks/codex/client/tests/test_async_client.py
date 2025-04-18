from io import BytesIO

import pytest
from urllib3.util import parse_url

from benchmarks.codex.client.async_client import AsyncCodexClientImpl
from benchmarks.core.concurrency import await_predicate_async
from benchmarks.core.utils.random import random_data
from benchmarks.core.utils.units import megabytes


@pytest.mark.codex_integration
@pytest.mark.asyncio
async def test_should_upload_file(codex_node_1_url: str):
    client = AsyncCodexClientImpl(parse_url(codex_node_1_url))

    data = BytesIO()
    random_data(megabytes(1), data)

    cid = client.upload(
        "test.txt", "application/octet-stream", BytesIO(data.getvalue())
    )
    assert cid is not None


@pytest.mark.codex_integration
@pytest.mark.asyncio
async def test_should_download_file(codex_node_1_url: str):
    client = AsyncCodexClientImpl(parse_url(codex_node_1_url))

    data = BytesIO()
    random_data(megabytes(5), data)

    cid = await client.upload(
        "test.txt", "application/octet-stream", BytesIO(data.getvalue())
    )
    assert cid is not None

    manifest = await client.manifest(cid)
    dataset_cid = await client.download(manifest)

    async def is_complete():
        status = await client.download_status(dataset_cid)
        assert status.total == manifest.block_count
        return status.is_complete()

    await await_predicate_async(is_complete, timeout=10)

    await client.leave_swarm(dataset_cid)
