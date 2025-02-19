from collections.abc import Iterator

import pytest

from benchmarks.codex.codex_node import CodexMeta
from benchmarks.core.experiments.dissemination_experiment.static import (
    StaticDisseminationExperiment,
)
from benchmarks.core.experiments.experiments import ExperimentEnvironment
from benchmarks.core.utils.units import megabytes


def merge_chunks(chunks: Iterator[bytes]) -> bytes:
    return b"".join(chunks)


@pytest.mark.codex_integration
def test_should_run_with_a_single_seeder(codex_node1, codex_node2, codex_node3):
    size = megabytes(2)
    env = ExperimentEnvironment(
        components=[codex_node1, codex_node2, codex_node3],
        polling_interval=0.5,
    )

    experiment = StaticDisseminationExperiment(
        network=[codex_node1, codex_node2, codex_node3],
        seeders=[1],
        file_size=size,
        seed=1234,
        meta=CodexMeta("dataset-1"),
    )

    env.await_ready()
    try:
        experiment.setup()
        experiment.do_run()

        all_datasets = list(codex_node1.hosted_datasets)
        assert len(all_datasets) == 1
        cid = all_datasets[0]

        content_1 = merge_chunks(codex_node1.download_local(cid))
        content_2 = merge_chunks(codex_node2.download_local(cid))
        content_3 = merge_chunks(codex_node3.download_local(cid))

        assert len(content_1) == megabytes(2)
        assert content_1 == content_2 == content_3

    finally:
        experiment.teardown()
