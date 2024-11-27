"""Basic definitions for structuring experiments."""

from abc import ABC, abstractmethod

from mypy.graph_utils import TypeVar


class Experiment(ABC):
    """An :class:`Experiment` is an arbitrary piece of code that can be run and measured."""

    @abstractmethod
    def run(self):
        """Synchronously runs the experiment, blocking the current thread until it's done."""
        pass


TExperiment = TypeVar('TExperiment', bound=Experiment)
