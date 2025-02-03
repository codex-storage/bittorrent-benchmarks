from benchmarks.logging.logging import Metric


class CodexDownloadMetric(Metric):
    name: str = "codex_download"
    cid: str
