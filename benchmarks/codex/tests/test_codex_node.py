from typing import cast

import pytest

from benchmarks.codex.agent.agent import DownloadStatus
from benchmarks.codex.codex_node import CodexMeta, CodexNode, CodexDownloadHandle
from benchmarks.core.utils.units import megabytes


@pytest.mark.codex_integration
def test_should_download_file(codex_node1: CodexNode, codex_node2: CodexNode):
    cid = codex_node1.genseed(
        size=megabytes(1),
        seed=1234,
        meta=CodexMeta(name="dataset1"),
    )
    handle = codex_node2.leech(cid)

    assert handle.await_for_completion(5)
    assert cast(CodexDownloadHandle, handle).completion() == DownloadStatus(
        downloaded=megabytes(1), total=megabytes(1)
    )
