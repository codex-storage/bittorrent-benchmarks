"""Basic utilities for structuring experiment configurations based on Pydantic schemas."""
import os
from abc import abstractmethod
from io import TextIOBase
from typing import Type, Dict, TextIO

import yaml
from typing_extensions import Generic, overload

from benchmarks.core.experiments.experiments import TExperiment
from benchmarks.core.pydantic import SnakeCaseModel


class ExperimentBuilder(SnakeCaseModel, Generic[TExperiment]):
    """:class:`ExperimentBuilders` can build real :class:`Experiment`s out of :class:`ConfigModel`s. """

    @abstractmethod
    def build(self) -> TExperiment:
        pass


class ConfigParser:
    """
    :class:`ConfigParser` is a utility class to parse configuration files into :class:`ExperimentBuilder`s.
    Currently, each :class:`ExperimentBuilder` can appear at most once in the config file.
    """

    def __init__(self):
        self.experiment_types = {}

    def register(self, root: Type[ExperimentBuilder[TExperiment]]):
        self.experiment_types[root.alias()] = root

    @overload
    def parse(self, data: dict) -> Dict[str, ExperimentBuilder[TExperiment]]:
        ...

    @overload
    def parse(self, data: TextIO) -> Dict[str, ExperimentBuilder[TExperiment]]:
        ...

    def parse(self, data: dict | TextIO) -> Dict[str, ExperimentBuilder[TExperiment]]:
        if isinstance(data, TextIOBase):
            entries = yaml.safe_load(os.path.expandvars(data.read()))
        else:
            entries = data

        return {
            tag: self.experiment_types[tag].model_validate(config)
            for tag, config in entries.items()
        }
