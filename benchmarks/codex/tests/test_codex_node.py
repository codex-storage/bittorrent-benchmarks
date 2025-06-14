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


@pytest.mark.codex_integration
def test_should_remove_file(codex_node1: CodexNode):
    cid = codex_node1.genseed(
        size=megabytes(1),
        seed=1234,
        meta=CodexMeta(name="dataset1"),
    )

    assert codex_node1.exists_local(cid)
    assert codex_node1.remove(cid)
    assert not codex_node1.exists_local(cid)


@pytest.mark.codex_integration
def test_should_turn_remove_file_into_noop_if_remove_file_flag_is_false(
    codex_node1: CodexNode,
):
    codex_node1.remove_data = False
    assert codex_node1.remove("malformed-and-invalid-cid")


@pytest.mark.codex_integration
def test_should_download_file_from_local_node(codex_node1: CodexNode):
    cid = codex_node1.genseed(
        size=megabytes(1),
        seed=1234,
        meta=CodexMeta(name="dataset1"),
    )

    contents = b"".join(codex_node1.download_local(cid))
    assert len(contents) == megabytes(1)
