"""Basic utilities for structuring experiment configurations based on Pydantic schemas."""

import os
from abc import abstractmethod
from io import TextIOBase
from typing import Type, Dict, TextIO

import yaml
from typing_extensions import Generic, overload, TypeVar

from benchmarks.core.pydantic import ConfigModel

T = TypeVar("T")


class Builder(ConfigModel, Generic[T]):
    """:class:`Builder` is a configuration model that can build useful objects."""

    @abstractmethod
    def build(self) -> T:
        pass


TBuilder = TypeVar("TBuilder", bound=Builder)


class ConfigParser(Generic[TBuilder]):
    """
    :class:`ConfigParser` is a utility class to parse configuration files into :class:`Builder`s.
    Currently, each :class:`Builder` type can appear at most once in the config file.
    """

    def __init__(self, ignore_unknown: bool = True) -> None:
        self.experiment_types: Dict[str, Type[TBuilder]] = {}
        self.ignore_unknown = ignore_unknown

    def register(self, root: Type[TBuilder]):
        self.experiment_types[root.alias()] = root

    @overload
    def parse(self, data: dict) -> Dict[str, TBuilder]: ...

    @overload
    def parse(self, data: TextIO) -> Dict[str, TBuilder]: ...

    def parse(self, data: dict | TextIO) -> Dict[str, TBuilder]:
        if isinstance(data, TextIOBase):
            entries = yaml.safe_load(os.path.expandvars(data.read()))
        else:
            entries = data

        return {
            tag: self.experiment_types[tag].model_validate(config)
            for tag, config in entries.items()
            if tag in self.experiment_types or not self.ignore_unknown
        }
