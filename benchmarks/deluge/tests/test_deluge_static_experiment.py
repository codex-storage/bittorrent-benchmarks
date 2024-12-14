import pytest

from benchmarks.core.experiments.experiments import ExperimentEnvironment
from benchmarks.core.experiments.static_experiment import StaticDisseminationExperiment
from benchmarks.core.utils import RandomTempData, megabytes
from benchmarks.deluge.deluge_node import DelugeMeta
from benchmarks.deluge.tests.test_deluge_node import assert_is_seed


@pytest.mark.integration
def test_should_run_with_a_single_seeder(
    tracker, deluge_node1, deluge_node2, deluge_node3
):
    size = megabytes(10)
    env = ExperimentEnvironment(
        components=[deluge_node1, deluge_node2, deluge_node3, tracker],
        polling_interval=0.5,
    )

    experiment = env.bind(
        StaticDisseminationExperiment(
            network=[deluge_node1, deluge_node2, deluge_node3],
            seeders=[1],
            data=RandomTempData(
                size=size,
                meta=DelugeMeta("dataset-1", announce_url=tracker.announce_url),
            ),
        )
    )

    experiment.run()

    assert_is_seed(deluge_node1, "dataset-1", size)
    assert_is_seed(deluge_node2, "dataset-1", size)
    assert_is_seed(deluge_node3, "dataset-1", size)


@pytest.mark.integration
def test_should_run_with_multiple_seeders(
    tracker, deluge_node1, deluge_node2, deluge_node3
):
    size = megabytes(10)
    env = ExperimentEnvironment(
        components=[deluge_node1, deluge_node2, deluge_node3, tracker],
        polling_interval=0.5,
    )

    experiment = env.bind(
        StaticDisseminationExperiment(
            network=[deluge_node1, deluge_node2, deluge_node3],
            seeders=[1, 2],
            data=RandomTempData(
                size=size,
                meta=DelugeMeta("dataset-1", announce_url=tracker.announce_url),
            ),
        )
    )

    experiment.run()

    assert_is_seed(deluge_node1, "dataset-1", size)
    assert_is_seed(deluge_node2, "dataset-1", size)
    assert_is_seed(deluge_node3, "dataset-1", size)
