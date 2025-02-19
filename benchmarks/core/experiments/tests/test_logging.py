from io import StringIO
from unittest.mock import patch

from benchmarks.core.experiments.experiments import Experiment
from benchmarks.core.experiments.logging import experiment_stage
from benchmarks.logging.logging import LogParser, ExperimentStage, EventBoundary


class SomeExperiment(Experiment):
    def __init__(self, should_raise=False):
        self.should_raise = should_raise

    def experiment_id(self):
        return "some-experiment"

    def run(self):
        with experiment_stage(self, "stage1"):
            pass

        with experiment_stage(self, "stage2"):
            if self.should_raise:
                raise RuntimeError("Error in experiment")


def test_should_log_experiment_stages(mock_logger):
    logger, output = mock_logger
    with patch("benchmarks.core.experiments.logging.logger", logger):
        experiment = SomeExperiment()
        experiment.run()

    parser = LogParser()
    parser.register(ExperimentStage)
    events = list(parser.parse(StringIO(output.getvalue())))

    assert events == [
        ExperimentStage(
            name="some-experiment",
            stage="stage1",
            type=EventBoundary.start,
            timestamp=events[0].timestamp,
        ),
        ExperimentStage(
            name="some-experiment",
            stage="stage1",
            type=EventBoundary.end,
            timestamp=events[1].timestamp,
        ),
        ExperimentStage(
            name="some-experiment",
            stage="stage2",
            type=EventBoundary.start,
            timestamp=events[2].timestamp,
        ),
        ExperimentStage(
            name="some-experiment",
            stage="stage2",
            type=EventBoundary.end,
            timestamp=events[3].timestamp,
        ),
    ]


def test_should_log_errors_when_thrown(mock_logger):
    logger, output = mock_logger
    with patch("benchmarks.core.experiments.logging.logger", logger):
        experiment = SomeExperiment(should_raise=True)
        try:
            experiment.run()
        except RuntimeError:
            pass

    parser = LogParser()
    parser.register(ExperimentStage)
    events = list(parser.parse(StringIO(output.getvalue())))

    assert events == [
        ExperimentStage(
            name="some-experiment",
            stage="stage1",
            type=EventBoundary.start,
            timestamp=events[0].timestamp,
        ),
        ExperimentStage(
            name="some-experiment",
            stage="stage1",
            type=EventBoundary.end,
            timestamp=events[1].timestamp,
        ),
        ExperimentStage(
            name="some-experiment",
            stage="stage2",
            type=EventBoundary.start,
            timestamp=events[2].timestamp,
        ),
        ExperimentStage(
            name="some-experiment",
            stage="stage2",
            type=EventBoundary.end,
            error="Error in experiment",
            timestamp=events[3].timestamp,
        ),
    ]
