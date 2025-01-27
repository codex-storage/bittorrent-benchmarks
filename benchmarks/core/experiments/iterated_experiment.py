import logging
import time
from typing import Iterable

from typing_extensions import Generic

from benchmarks.core.experiments.experiments import Experiment, TExperiment
from benchmarks.logging.logging import ExperimentStatus

logger = logging.getLogger(__name__)


class IteratedExperiment(Experiment, Generic[TExperiment]):
    """An :class:`IteratedExperiment` will run a sequence of :class:`Experiment`s."""

    def __init__(
        self,
        experiments: Iterable[TExperiment],
        experiment_set_id: str = "unnamed",
        raise_when_failures: bool = True,
    ):
        self.experiment_set_id = experiment_set_id
        self.successful_runs = 0
        self.failed_runs = 0
        self.raise_when_failures = raise_when_failures
        self.experiments = experiments

    def run(self):
        for i, experiment in enumerate(self.experiments):
            start = time.time()
            try:
                experiment.run()
                self.successful_runs += 1
                logger.info(
                    ExperimentStatus(
                        name=self.experiment_set_id,
                        repetition=i,
                        duration=time.time() - start,
                    )
                )
            except Exception as ex:
                self.failed_runs += 1
                logger.exception("Error running experiment repetition")
                logger.info(
                    ExperimentStatus(
                        name=self.experiment_set_id,
                        repetition=i,
                        duration=time.time() - start,
                        error=str(ex),
                    )
                )

        if self.failed_runs > 0 and self.raise_when_failures:
            raise RuntimeError(
                "One or more experiments with an iterated experiment have failed."
            )
