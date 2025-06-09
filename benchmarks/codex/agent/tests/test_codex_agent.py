import asyncio
from io import StringIO
from unittest.mock import patch

import pytest

from benchmarks.codex.agent.agent import CodexAgent, DownloadStatus
from benchmarks.codex.agent.tests.fake_codex import FakeCodex, fake_codex_api
from benchmarks.codex.client.async_client import AsyncCodexClientImpl
from benchmarks.core.concurrency import await_predicate_async
from benchmarks.logging.logging import LogParser, DownloadMetric


@pytest.mark.asyncio
async def test_should_create_dataset_of_right_size():
    codex_agent = CodexAgent(FakeCodex())
    cid = await codex_agent.create_dataset(size=1024, name="dataset-1", seed=1234)
    manifest = await codex_agent.client.manifest(cid)

    assert manifest.datasetSize == 1024


@pytest.mark.asyncio
async def test_same_seed_creates_same_cid():
    codex_agent = CodexAgent(FakeCodex())

    cid1 = await codex_agent.create_dataset(size=2048, name="dataset-1", seed=1234)
    cid2 = await codex_agent.create_dataset(size=2048, name="dataset-1", seed=1234)
    cid3 = await codex_agent.create_dataset(size=2048, name="dataset-1", seed=1235)

    assert cid1 == cid2
    assert cid1 != cid3


@pytest.mark.asyncio
async def test_should_report_download_progress():
    client = FakeCodex()
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
    client = FakeCodex()
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
        client = FakeCodex()
        codex_agent = CodexAgent(client)

        cid = await codex_agent.create_dataset(size=1000, name="dataset-1", seed=1234)

        download_stream = client.create_download_stream(cid)
        download_stream.feed_data(b"0" * 1000)
        download_stream.feed_eof()

        handle = await codex_agent.download(cid, read_increment=0.2)
        await handle.download_task

    parser = LogParser()
    parser.register(DownloadMetric)

    metrics = list(parser.parse(StringIO(output.getvalue())))

    assert metrics == [
        DownloadMetric(
            dataset_name="dataset-1",
            value=200,
            node=codex_agent.node_id,
            timestamp=metrics[0].timestamp,
        ),
        DownloadMetric(
            dataset_name="dataset-1",
            value=400,
            node=codex_agent.node_id,
            timestamp=metrics[1].timestamp,
        ),
        DownloadMetric(
            dataset_name="dataset-1",
            value=600,
            node=codex_agent.node_id,
            timestamp=metrics[2].timestamp,
        ),
        DownloadMetric(
            dataset_name="dataset-1",
            value=800,
            node=codex_agent.node_id,
            timestamp=metrics[3].timestamp,
        ),
        DownloadMetric(
            dataset_name="dataset-1",
            value=1000,
            node=codex_agent.node_id,
            timestamp=metrics[4].timestamp,
        ),
    ]


@pytest.mark.asyncio
async def test_should_log_download_progress_as_discrete_steps_even_when_underlying_stream_is_choppy(
    mock_logger,
):
    logger, output = mock_logger

    with patch("benchmarks.codex.agent.agent.logger", logger):
        client = FakeCodex()
        codex_agent = CodexAgent(client)
        cid = await codex_agent.create_dataset(size=1000, name="dataset-1", seed=1234)
        download_stream = client.create_download_stream(cid)
        handle = await codex_agent.download(cid, read_increment=0.2)

        # Simulates a choppy download which returns a lot less than the logging step size every time.
        fed = 0
        step = 37
        while fed < 1000:
            to_feed = min(step, 1000 - fed)
            download_stream.feed_data(b"0" * to_feed)
            fed += to_feed
            assert await await_predicate_async(
                lambda: handle.progress() == DownloadStatus(downloaded=fed, total=1000),
                timeout=5,
            )

        download_stream.feed_eof()
        await handle.download_task

    parser = LogParser()
    parser.register(DownloadMetric)

    metrics = list(parser.parse(StringIO(output.getvalue())))

    assert metrics == [
        DownloadMetric(
            dataset_name="dataset-1",
            value=200,
            node=codex_agent.node_id,
            timestamp=metrics[0].timestamp,
        ),
        DownloadMetric(
            dataset_name="dataset-1",
            value=400,
            node=codex_agent.node_id,
            timestamp=metrics[1].timestamp,
        ),
        DownloadMetric(
            dataset_name="dataset-1",
            value=600,
            node=codex_agent.node_id,
            timestamp=metrics[2].timestamp,
        ),
        DownloadMetric(
            dataset_name="dataset-1",
            value=800,
            node=codex_agent.node_id,
            timestamp=metrics[3].timestamp,
        ),
        DownloadMetric(
            dataset_name="dataset-1",
            value=1000,
            node=codex_agent.node_id,
            timestamp=metrics[4].timestamp,
        ),
    ]


@pytest.mark.asyncio
async def test_should_log_download_progress_even_when_log_granularity_larger_than_number_of_bytes(
    mock_logger,
):
    logger, output = mock_logger

    with patch("benchmarks.codex.agent.agent.logger", logger):
        client = FakeCodex()
        codex_agent = CodexAgent(client)
        cid = await codex_agent.create_dataset(size=3, name="dataset-1", seed=1234)
        download_stream = client.create_download_stream(cid)
        handle = await codex_agent.download(cid, read_increment=0.1)

        download_stream.feed_data(b"0" * 3)
        download_stream.feed_eof()

        await handle.download_task

    parser = LogParser()
    parser.register(DownloadMetric)

    metrics = list(parser.parse(StringIO(output.getvalue())))

    assert metrics == [
        DownloadMetric(
            dataset_name="dataset-1",
            value=1,
            node=codex_agent.node_id,
            timestamp=metrics[0].timestamp,
        ),
        DownloadMetric(
            dataset_name="dataset-1",
            value=2,
            node=codex_agent.node_id,
            timestamp=metrics[1].timestamp,
        ),
        DownloadMetric(
            dataset_name="dataset-1",
            value=3,
            node=codex_agent.node_id,
            timestamp=metrics[2].timestamp,
        ),
    ]


@pytest.mark.asyncio
async def test_should_track_download_handles():
    client = FakeCodex()
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


@pytest.mark.asyncio
async def test_should_timeout_if_download_stream_takes_too_long_to_return_content():
    async with fake_codex_api() as (fake_codex, url):
        client = AsyncCodexClientImpl(url)
        codex_agent = CodexAgent(client, read_timeout=0.5)

        fast_cid = await codex_agent.create_dataset(
            size=1000, name="dataset-fast-1", seed=1356
        )
        slow_cid = await codex_agent.create_dataset(
            size=1000, name="dataset-slow-1", seed=1353
        )

        fast_download = fake_codex.create_download_stream(fast_cid)
        slow_download = fake_codex.create_download_stream(slow_cid)

        fast_download.feed_data(b"0" * 1000)
        fast_download.feed_eof()
        fast_handle = await codex_agent.download(fast_cid)
        await fast_handle.download_task

        slow_handle = await codex_agent.download(slow_cid)
        slow_download.feed_data(b"0" * 500)
        await asyncio.sleep(0.6)
        slow_download.feed_data(b"0" * 500)
        slow_download.feed_eof()

        with pytest.raises(asyncio.TimeoutError):
            await slow_handle.download_task
