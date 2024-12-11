from benchmarks.core.tests.test_logging import MetricsEvent


class DelugeTorrentDownload(MetricsEvent):
    torrent_name: str