"""Basic utilities for structuring experiment configurations based on Pydantic schemas."""
import os
import re
from abc import abstractmethod
from io import TextIOBase
from typing import Annotated, Type, Dict, TextIO, Callable, cast

import yaml
from pydantic import BaseModel, IPvAnyAddress, AfterValidator, TypeAdapter
from typing_extensions import Generic, overload

from benchmarks.core.experiments.experiments import TExperiment, Experiment


def drop_config_suffix(name: str) -> str:
    return name[:-6] if name.endswith('Config') else name


def to_snake_case(name: str) -> str:
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


class ConfigModel(BaseModel):
    model_config = {
        'alias_generator': lambda x: to_snake_case(drop_config_suffix(x))
    }


# This is a simple regex which is not by any means exhaustive but should cover gross syntax errors.
VALID_DOMAIN_NAME = re.compile(r"^localhost$|^(?!-)([A-Za-z0-9-]+\.)+[A-Za-z]{2,6}$")


def is_valid_domain_name(domain_name: str):
    stripped = domain_name.strip()
    matches = VALID_DOMAIN_NAME.match(stripped)
    assert matches is not None
    return stripped


DomainName = Annotated[str, AfterValidator(is_valid_domain_name)]

type Host = IPvAnyAddress | DomainName


class ExperimentBuilder(ConfigModel, Generic[TExperiment]):
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
        name = root.__name__
        alias = cast(Callable[[str], str],
                     root.model_config.get('alias_generator', lambda x: x))(name)
        self.experiment_types[alias] = root

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
