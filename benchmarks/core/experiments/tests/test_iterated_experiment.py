from benchmarks.core.experiments.experiments import Experiment
from benchmarks.core.experiments.iterated_experiment import IteratedExperiment


class SimpleExperiment(Experiment):
    def __init__(self):
        self.ran = False

    def run(self):
        self.ran = True


def test_should_run_experiment_repetitions():
    experiments = [
        SimpleExperiment(),
        SimpleExperiment(),
        SimpleExperiment(),
    ]

    iterated_experiment = IteratedExperiment(experiments)
    iterated_experiment.run()

    assert iterated_experiment.successful_runs == 3

    assert all(experiment.ran for experiment in experiments)


def test_should_register_failed_repetitions():
    class FailingExperiment(Experiment):
        def run(self):
            raise RuntimeError("This experiment failed.")

    experiments = [
        SimpleExperiment(),
        FailingExperiment(),
        SimpleExperiment(),
    ]

    iterated_experiment = IteratedExperiment(experiments, raise_when_failures=False)
    iterated_experiment.run()

    assert iterated_experiment.successful_runs == 2
    assert iterated_experiment.failed_runs == 1

    assert all(
        experiment.ran
        for experiment in experiments
        if not isinstance(experiment, FailingExperiment)
    )
