"""Basic definitions for structuring experiments."""

import logging
import random
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import List, Optional

from typing_extensions import Generic, TypeVar

from benchmarks.core.concurrency import await_predicate
from benchmarks.core.config import Builder

logger = logging.getLogger(__name__)


class Experiment(ABC):
    """Base interface for an executable :class:`Experiment`."""

    @abstractmethod
    def run(self):
        """Synchronously runs the experiment, blocking the current thread until it's done."""
        pass


TExperiment = TypeVar("TExperiment", bound=Experiment)

ExperimentBuilder = Builder[TExperiment]


class ExperimentWithLifecycle(Experiment):
    """An :class:`ExperimentWithLifecycle` is a basic implementation of an :class:`Experiment` with overridable
    lifecycle hooks."""

    def setup(self):
        """Hook that runs before the experiment."""
        pass

    def run(self):
        try:
            self.setup()
            self.do_run()
            self.teardown()
        except Exception as ex:
            self.teardown(ex)
            raise ex

    def do_run(self):
        """The main body of the experiment."""
        pass

    def teardown(self, exception: Optional[Exception] = None):
        """Hook that runs after the experiment."""
        pass


class ExperimentComponent(ABC):
    """An :class:`ExperimentComponent` is a part of the environment for an experiment. These could be databases,
    network nodes, etc."""

    @abstractmethod
    def is_ready(self) -> bool:
        """Returns whether this component is ready or not."""
        pass


class ExperimentEnvironment(ExperimentComponent):
    """An :class:`ExperimentEnvironment` is a collection of :class:`ExperimentComponent`s that must be ready before
    an :class:`Experiment` can execute. Note that we assume that readiness is stable; i.e., if a component is ready
    at some point, then it will remain ready for the duration of the experiment."""

    def __init__(
        self,
        components: Iterable[ExperimentComponent],
        ping_max: int = 10,
        polling_interval: float = 0,
    ):
        self.components = components
        self.polling_interval = polling_interval
        self.ping_max = ping_max
        self.not_ready = list(components)

    def await_ready(self, timeout: float = 0) -> bool:
        """Awaits for all components to be ready, or until a timeout is reached."""
        logging.info(
            f"Awaiting for components to be ready: {self._component_names(self.not_ready)}"
        )

        if not await_predicate(self.is_ready, timeout, self.polling_interval):
            logger.info(
                f"Some components timed out: {self._component_names(self.not_ready)}"
            )
            return False

        return True

    def is_ready(self) -> bool:
        for component in self._draw(self.not_ready):
            if component.is_ready():
                logger.info(f"Component {str(component)} is ready.")
                self.not_ready.remove(component)

        return len(self.not_ready) == 0

    def _draw(self, components: List[ExperimentComponent]) -> List[ExperimentComponent]:
        if len(components) <= self.ping_max:
            return components

        random.shuffle(components)
        return components[: self.ping_max]

    @staticmethod
    def _component_names(components: List[ExperimentComponent]) -> str:
        return ", ".join(str(component) for component in components)

    def run(self, experiment: Experiment):
        """Runs the :class:`Experiment` within this :class:`ExperimentEnvironment`."""
        if not self.await_ready():
            raise RuntimeError(
                "One or more environment components were not get ready in time"
            )

        experiment.run()

    def bind(self, experiment: TExperiment) -> "BoundExperiment[TExperiment]":
        return BoundExperiment(experiment, self)


class BoundExperiment(Experiment, Generic[TExperiment]):
    def __init__(self, experiment: Experiment, env: ExperimentEnvironment):
        self.experiment = experiment
        self.env = env

    def run(self):
        self.env.run(self.experiment)
