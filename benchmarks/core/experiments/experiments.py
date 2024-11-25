from abc import ABC, abstractmethod

from typing_extensions import Generic, TypeVar

TRunnableExperiment = TypeVar('TRunnableExperiment', bound='RunnableExperiment')


class Experiment(Generic[TRunnableExperiment]):
    """An :class:`Experiment` represents a self-contained experimental unit which may be repeated
    multiple times. :class:`Experiment`s, unlike tests, have the generation of metrics as a side effect
    as their main outcome."""

    @abstractmethod
    def setup(self) -> TRunnableExperiment:
        pass


class RunnableExperiment(ABC):
    def run(self):
        try:
            self._run()
        finally:
            self.teardown()

    @abstractmethod
    def _run(self):
        pass

    def teardown(self):
        pass
