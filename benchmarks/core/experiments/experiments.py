"""Basic definitions for structuring experiments."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Iterable
from time import time, sleep
from typing import Optional, List

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

        start_time = time()
        not_ready = [component for component in self.components]

        logging.info(f'Awaiting for components to be ready: {self._component_names(not_ready)}')
        while len(not_ready) != 0:
            for component in not_ready:
                if component.is_ready():
                    logger.info(f'Component {str(component)} is ready.')
                    not_ready.remove(component)

            sleep(self.polling_interval)

            if (timeout != 0) and (time() - start_time > timeout):
                print("timeout")
                logger.info(f'Some components timed out: {self._component_names(not_ready)}')
                return False

        return True

    @staticmethod
    def _component_names(components: List[ExperimentComponent]) -> str:
        return ', '.join(str(component) for component in components)

    def run(self, experiment: Experiment):
        """Runs the :class:`Experiment` within this :class:`ExperimentEnvironment`."""
        if not self.await_ready():
            raise RuntimeError('One or more environment components were not get ready in time')

        experiment.run()

    def bind(self, experiment: TExperiment) -> 'BoundExperiment[TExperiment]':
        return BoundExperiment(experiment, self)


class BoundExperiment(Experiment, Generic[TExperiment]):
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
