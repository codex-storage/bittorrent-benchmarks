import asyncio
from io import StringIO
from unittest.mock import patch

import pytest

from benchmarks.codex.agent.agent import CodexAgent, DownloadStatus
from benchmarks.codex.agent.tests.fake_codex import FakeCodex
from benchmarks.core.concurrency import await_predicate_async
from benchmarks.logging.logging import LogParser, DownloadMetric


@pytest.mark.asyncio
async def test_should_create_dataset_of_right_size():
    codex_agent = CodexAgent(FakeCodex())
    manifest = await codex_agent.create_dataset(size=1024, name="dataset-1", seed=1234)

    assert manifest.datasetSize == 1024


@pytest.mark.asyncio
async def test_same_seed_creates_same_cid():
    codex_agent = CodexAgent(FakeCodex())

    manifest1 = await codex_agent.create_dataset(size=2048, name="dataset-1", seed=1234)
    manifest2 = await codex_agent.create_dataset(size=2048, name="dataset-1", seed=1234)
    manifest3 = await codex_agent.create_dataset(size=2048, name="dataset-1", seed=1235)

    assert manifest1.cid == manifest2.cid
    assert manifest1.cid != manifest3.cid


@pytest.mark.asyncio
async def test_should_report_download_progress():
    client = FakeCodex()
    codex_agent = CodexAgent(client, status_backoff=0.01)

    manifest = await codex_agent.create_dataset(size=1000, name="dataset-1", seed=1234)
    fake_download = client.new_download(manifest)
    handle = await codex_agent.download(manifest)

    assert handle.progress() == DownloadStatus(downloaded=0, total=1000)

    for i in range(200):
        fake_download.advance_download(blocks=5)
        assert await await_predicate_async(
            lambda: handle.progress()
            == DownloadStatus(downloaded=5 * (i + 1), total=1000),
            timeout=5,
        )

    await handle.download_task

    assert handle.progress() == DownloadStatus(downloaded=1000, total=1000)


@pytest.mark.asyncio
async def test_should_raise_exception_on_progress_query_if_download_fails():
    client = FakeCodex()
    codex_agent = CodexAgent(client)

    manifest = await codex_agent.create_dataset(size=1000, name="dataset-1", seed=1234)
    fake_download = client.new_download(manifest)

    handle = await codex_agent.download(manifest)

    class SomeError(Exception):
        pass

    fake_download.abort(SomeError())

    with pytest.raises(SomeError):
        await handle.download_task


@pytest.mark.asyncio
async def test_should_log_download_progress_as_metric_in_discrete_steps(mock_logger):
    logger, output = mock_logger

    with patch("benchmarks.codex.agent.agent.logger", logger):
        client = FakeCodex()
        codex_agent = CodexAgent(client)

        manifest = await codex_agent.create_dataset(
            size=1000, name="dataset-1", seed=1234
        )
        fake_download = client.new_download(manifest)

        fake_download.advance_download(1000)

        handle = await codex_agent.download(manifest, log_increment=0.2)
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
        codex_agent = CodexAgent(client, status_backoff=0.01)
        manifest = await codex_agent.create_dataset(
            size=1000, name="dataset-1", seed=1234
        )
        fake_download = client.new_download(manifest)
        handle = await codex_agent.download(manifest, log_increment=0.2)
        # Simulates a choppy download which returns a lot less than the logging step size every time.
        fed = 0
        step = 37
        while fed < 1000:
            to_feed = min(step, 1000 - fed)
            fake_download.advance_download(to_feed)
            fed += to_feed
            assert await await_predicate_async(
                lambda: handle.progress() == DownloadStatus(downloaded=fed, total=1000),
                timeout=5,
            )

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
async def test_should_track_download_handles():
    client = FakeCodex()
    codex_agent = CodexAgent(client)

    manifest = await codex_agent.create_dataset(size=1000, name="dataset-1", seed=1356)
    fake_download = client.new_download(manifest)

    assert manifest.treeCid not in codex_agent.ongoing_downloads

    handle = await codex_agent.download(manifest)
    assert codex_agent.ongoing_downloads[manifest.treeCid] == handle

    fake_download.advance_download(1000)
    await handle.download_task
    assert manifest.treeCid in codex_agent.ongoing_downloads


@pytest.mark.asyncio
async def test_should_timeout_if_download_goes_for_too_long_without_any_progress():
    fake_codex = FakeCodex()
    codex_agent = CodexAgent(fake_codex, status_backoff=0.01, progress_timeout=0.5)

    fast = await codex_agent.create_dataset(size=1000, name="dataset-fast-1", seed=1356)
    slow = await codex_agent.create_dataset(size=1000, name="dataset-slow-1", seed=1353)

    fast_download = fake_codex.new_download(fast)
    slow_download = fake_codex.new_download(slow)

    fast_download.advance_download(1000)
    fast_handle = await codex_agent.download(fast)
    await fast_handle.download_task

    slow_handle = await codex_agent.download(slow)
    slow_download.advance_download(500)
    await asyncio.sleep(0.6)
    slow_download.advance_download(500)

    with pytest.raises(asyncio.TimeoutError):
        await slow_handle.download_task
