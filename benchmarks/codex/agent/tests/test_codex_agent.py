from asyncio import StreamReader
from contextlib import asynccontextmanager
from io import StringIO
from typing import IO, Dict, AsyncIterator
from unittest.mock import patch

import pytest

from benchmarks.codex.agent.agent import CodexAgent, DownloadStatus
from benchmarks.codex.client.async_client import AsyncCodexClient
from benchmarks.codex.client.common import Manifest, Cid
from benchmarks.codex.logging import CodexDownloadMetric
from benchmarks.core.concurrency import await_predicate_async
from benchmarks.core.utils.streams import BaseStreamReader
from benchmarks.logging.logging import LogParser


class FakeCodexClient(AsyncCodexClient):
    def __init__(self) -> None:
        self.storage: Dict[Cid, Manifest] = {}
        self.streams: Dict[Cid, StreamReader] = {}

    async def upload(self, name: str, mime_type: str, content: IO) -> Cid:
        data = content.read()
        cid = "Qm" + str(hash(data))
        self.storage[cid] = Manifest(
            cid=cid,
            datasetSize=len(data),
            mimetype=mime_type,
            blockSize=1,
            filename=name,
            treeCid="",
            uploadedAt=0,
            protected=False,
        )
        return cid

    async def manifest(self, cid: Cid) -> Manifest:
        return self.storage[cid]

    def create_download_stream(self, cid: Cid) -> StreamReader:
        reader = StreamReader()
        self.streams[cid] = reader
        return reader

    @asynccontextmanager
    async def download(self, cid: Cid) -> AsyncIterator[BaseStreamReader]:
        yield self.streams[cid]


@pytest.mark.asyncio
async def test_should_create_dataset_of_right_size():
    codex_agent = CodexAgent(FakeCodexClient())
    cid = await codex_agent.create_dataset(size=1024, name="dataset-1", seed=1234)
    manifest = await codex_agent.client.manifest(cid)

    assert manifest.datasetSize == 1024


@pytest.mark.asyncio
async def test_same_seed_creates_same_cid():
    codex_agent = CodexAgent(FakeCodexClient())

    cid1 = await codex_agent.create_dataset(size=2048, name="dataset-1", seed=1234)
    cid2 = await codex_agent.create_dataset(size=2048, name="dataset-1", seed=1234)
    cid3 = await codex_agent.create_dataset(size=2048, name="dataset-1", seed=1235)

    assert cid1 == cid2
    assert cid1 != cid3


@pytest.mark.asyncio
async def test_should_report_download_progress():
    client = FakeCodexClient()
    codex_agent = CodexAgent(client)

    cid = await codex_agent.create_dataset(size=1000, name="dataset-1", seed=1234)
    download_stream = client.create_download_stream(cid)

    handle = await codex_agent.download(cid)

    assert handle.progress() == DownloadStatus(downloaded=0, total=1000)

    for i in range(200):
        download_stream.feed_data(b"0" * 5)
        assert await await_predicate_async(
            lambda: handle.progress()
            == DownloadStatus(downloaded=5 * (i + 1), total=1000),
            timeout=5,
        )

    download_stream.feed_eof()
    await handle.download_task

    assert handle.progress() == DownloadStatus(downloaded=1000, total=1000)


@pytest.mark.asyncio
async def test_should_raise_exception_on_progress_query_if_download_fails():
    client = FakeCodexClient()
    codex_agent = CodexAgent(client)

    cid = await codex_agent.create_dataset(size=1000, name="dataset-1", seed=1234)
    download_stream = client.create_download_stream(cid)

    handle = await codex_agent.download(cid)

    download_stream.feed_eof()

    with pytest.raises(EOFError):
        await handle.download_task


@pytest.mark.asyncio
async def test_should_log_download_progress_as_metric_in_discrete_steps(mock_logger):
    logger, output = mock_logger

    with patch("benchmarks.codex.agent.agent.logger", logger):
        client = FakeCodexClient()
        codex_agent = CodexAgent(client)

        cid = await codex_agent.create_dataset(size=1000, name="dataset-1", seed=1234)

        download_stream = client.create_download_stream(cid)
        download_stream.feed_data(b"0" * 1000)
        download_stream.feed_eof()

        handle = await codex_agent.download(cid, read_increment=0.2)
        await handle.download_task

    parser = LogParser()
    parser.register(CodexDownloadMetric)

    metrics = list(parser.parse(StringIO(output.getvalue())))

    assert metrics == [
        CodexDownloadMetric(
            cid=cid, value=200, node=codex_agent.node_id, timestamp=metrics[0].timestamp
        ),
        CodexDownloadMetric(
            cid=cid, value=400, node=codex_agent.node_id, timestamp=metrics[1].timestamp
        ),
        CodexDownloadMetric(
            cid=cid, value=600, node=codex_agent.node_id, timestamp=metrics[2].timestamp
        ),
        CodexDownloadMetric(
            cid=cid, value=800, node=codex_agent.node_id, timestamp=metrics[3].timestamp
        ),
        CodexDownloadMetric(
            cid=cid,
            value=1000,
            node=codex_agent.node_id,
            timestamp=metrics[4].timestamp,
        ),
    ]


@pytest.mark.asyncio
async def test_should_track_download_handles():
    client = FakeCodexClient()
    codex_agent = CodexAgent(client)

    cid = await codex_agent.create_dataset(size=1000, name="dataset-1", seed=1356)

    assert cid not in codex_agent.ongoing_downloads

    download_stream = client.create_download_stream(cid)
    handle = await codex_agent.download(cid)

    download_stream.feed_data(b"0" * 1000)
    download_stream.feed_eof()

    assert codex_agent.ongoing_downloads[cid] == handle

    await handle.download_task

    assert cid in codex_agent.ongoing_downloads
