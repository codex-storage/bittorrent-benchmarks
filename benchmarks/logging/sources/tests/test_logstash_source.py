import pytest

from benchmarks.deluge.logging import DelugeTorrentDownload
from benchmarks.logging.logging import LogParser
from datetime import datetime, timezone

from benchmarks.logging.sources.logstash import LogstashSource


def _log_lines(source, experiment_id, group_id):
    return (
        rawline
        for _, _, rawline in source.logs(experiment_id=experiment_id, group_id=group_id)
    )


@pytest.mark.integration
def test_should_retrieve_unstructured_log_messages(benchmark_logs_client):
    source = LogstashSource(benchmark_logs_client, chronological=True)
    lines = list(_log_lines(source, "e3", "g3"))
    assert not all(">>" in line for line in lines)


def test_filter_out_unstructured_log_messages(benchmark_logs_client):
    source = LogstashSource(
        benchmark_logs_client, structured_only=True, chronological=True
    )
    lines = list(_log_lines(source, "e3", "g3"))
    assert all(">>" in line for line in lines)


@pytest.mark.integration
def test_should_retrieve_logs_for_single_experiment(benchmark_logs_client):
    source = LogstashSource(
        benchmark_logs_client, structured_only=True, chronological=True
    )

    parser = LogParser()
    parser.register(DelugeTorrentDownload)

    entries = parser.parse(_log_lines(source, "e3", "g3"))

    assert list(entries) == [
        DelugeTorrentDownload(
            name="deluge_piece_downloaded",
            timestamp=datetime(2025, 1, 21, 12, 47, 15, 846761, tzinfo=timezone.utc),
            value=23,
            node="deluge-nodes-e3-g3-0",
            torrent_name="dataset-0-0",
        ),
        DelugeTorrentDownload(
            name="deluge_piece_downloaded",
            timestamp=datetime(2025, 1, 21, 12, 47, 57, 98167, tzinfo=timezone.utc),
            value=310,
            node="deluge-nodes-e3-g3-1",
            torrent_name="dataset-0-1",
        ),
    ]

    entries = parser.parse(_log_lines(source, "e2", "g3"))

    assert list(entries) == [
        DelugeTorrentDownload(
            name="deluge_piece_downloaded",
            timestamp=datetime(2025, 1, 21, 12, 47, 57, 123105, tzinfo=timezone.utc),
            value=218,
            node="deluge-nodes-e2-g2-1",
            torrent_name="dataset-0-1",
        ),
    ]


@pytest.mark.integration
def test_should_return_empty_data_for_non_existing_experiments(benchmark_logs_client):
    source = LogstashSource(
        benchmark_logs_client, structured_only=True, chronological=True
    )

    parser = LogParser()
    parser.register(DelugeTorrentDownload)

    lines = source.logs(experiment_id="e0", group_id="g0")

    assert list(lines) == []


@pytest.mark.integration
def test_should_return_all_experiments_within_a_group(benchmark_logs_client):
    source = LogstashSource(
        benchmark_logs_client, structured_only=True, chronological=True
    )
    assert sorted(list(source.experiments(group_id="g3"))) == ["e2", "e3"]
