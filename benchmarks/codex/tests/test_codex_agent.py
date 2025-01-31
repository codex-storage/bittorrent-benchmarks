from asyncio import StreamReader
from typing import IO, Dict

import pytest

from benchmarks.codex.agent import CodexAgent
from benchmarks.codex.client import CodexClient, Cid, Manifest
from benchmarks.core.concurrency import await_predicate_async
from benchmarks.core.utils.streams import BaseStreamReader


class FakeCodexClient(CodexClient):
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

    async def get_manifest(self, cid: Cid) -> Manifest:
        return self.storage[cid]

    def create_download_stream(self, cid: Cid) -> StreamReader:
        reader = StreamReader()
        self.streams[cid] = reader
        return reader

    async def download(self, cid: Cid) -> BaseStreamReader:
        return self.streams[cid]


@pytest.mark.asyncio
async def test_should_create_dataset_of_right_size():
    codex_agent = CodexAgent(FakeCodexClient())
    cid = await codex_agent.create_dataset(size=1024, name="dataset-1", seed=1234)
    manifest = await codex_agent.client.get_manifest(cid)

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

    assert handle.progress() == 0

    for i in range(100):
        download_stream.feed_data(b"0" * 5)
        assert len(download_stream._buffer) == 5
        assert await await_predicate_async(
            lambda: round(handle.progress() * 100) == i, timeout=5
        )
        assert await await_predicate_async(
            lambda: len(download_stream._buffer) == 0, timeout=5
        )

        download_stream.feed_data(b"0" * 5)
        assert len(download_stream._buffer) == 5
        assert await await_predicate_async(
            lambda: round(handle.progress() * 100) == (i + 1), timeout=5
        )
        assert await await_predicate_async(
            lambda: len(download_stream._buffer) == 0, timeout=5
        )

    download_stream.feed_eof()
    await handle.download_task


@pytest.mark.asyncio
async def test_should_raise_exception_on_progress_query_if_download_fails():
    client = FakeCodexClient()
    codex_agent = CodexAgent(client)

    cid = await codex_agent.create_dataset(size=1000, name="dataset-1", seed=1234)
    download_stream = client.create_download_stream(cid)

    handle = await codex_agent.download(cid)

    download_stream.feed_eof()

    with pytest.raises(EOFError):

        def _predicate():
            handle.progress()
            return False

        await await_predicate_async(_predicate, timeout=5)
