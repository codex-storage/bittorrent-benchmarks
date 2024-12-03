"""Basic definitions for structuring experiments."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Optional

from typing_extensions import Generic, TypeVar

from benchmarks.core.utils import await_predicate

logger = logging.getLogger(__name__)


class Experiment(ABC):
    """Base interface for an executable :class:`Experiment`."""

    @abstractmethod
    def run(self):
        """Synchronously runs the experiment, blocking the current thread until it's done."""
        pass


TExperiment = TypeVar('TExperiment', bound=Experiment)


class ExperimentComponent(ABC):
    """An :class:`ExperimentComponent` is a part of the environment for an experiment. These could be databases,
    network nodes, etc."""

    @abstractmethod
    def is_ready(self) -> bool:
        """Returns whether this component is ready or not."""
        pass


class ExperimentEnvironment:
    """An :class:`ExperimentEnvironment` is a collection of :class:`ExperimentComponent`s that must be ready before
    an :class:`Experiment` can execute."""

    def __init__(self, components: Iterable[ExperimentComponent], polling_interval: float = 0):
        self.components = components
        self.polling_interval = polling_interval

    def await_ready(self, timeout: float = 0) -> bool:
        """Awaits for all components to be ready, or until a timeout is reached."""
        # TODO we should probably have per-component timeouts, or at least provide feedback
        #  as to what was the completion state of each component.
        if not await_predicate(
                lambda: all(component.is_ready() for component in self.components),
                timeout=timeout,
                polling_interval=self.polling_interval,
        ):
            return False

        return True

    def run(self, experiment: Experiment):
        """Runs the :class:`Experiment` within this :class:`ExperimentEnvironment`."""
        if not self.await_ready():
            raise RuntimeError('One or more environment components were not get ready in time')

        experiment.run()

    def bind(self, experiment: TExperiment) -> Experiment:
        return _BoundExperiment(experiment, self)


class _BoundExperiment(Experiment, ABC):
    def __init__(self, experiment: Experiment, env: ExperimentEnvironment):
        self.experiment = experiment
        self.env = env

    def run(self):
        self.env.run(self.experiment)


class IteratedExperiment(Experiment, Generic[TExperiment]):
    """An :class:`IteratedExperiment` will run a sequence of :class:`Experiment`s."""

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
