"""Basic definitions for structuring experiments."""

from abc import ABC, abstractmethod
from collections.abc import Iterable

from mypy.graph_utils import TypeVar

import logging

from typing_extensions import Generic

logger = logging.getLogger(__name__)


class Experiment(ABC):
    @abstractmethod
    def run(self):
        """Synchronously runs the experiment, blocking the current thread until it's done."""
        pass


TExperiment = TypeVar('TExperiment', bound=Experiment)


class IteratedExperiment(Experiment, Generic[TExperiment]):
    """An :class:`IteratedExperiment` will a sequence of :class:`Experiment`s."""

    def __init__(self, experiments: Iterable[TExperiment]):
        self.successful_runs = 0
        self.failed_runs = 0
        self.experiments = experiments

    def run(self):
        for experiment in self.experiments:
            try:
                experiment.run()
                self.successful_runs += 1
            except Exception as ex:
                self.failed_runs += 1
                logger.error(ex)
