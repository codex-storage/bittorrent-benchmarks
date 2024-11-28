"""Basic utilities for structuring experiment configurations based on Pydantic schemas."""

import re
from abc import abstractmethod
from typing import Annotated

from pydantic import BaseModel, IPvAnyAddress, AfterValidator
from typing_extensions import Generic

from benchmarks.core.experiments.experiments import TExperiment


def drop_config_suffix(name: str) -> str:
    return name[:-6] if name.endswith('Config') else name


class ConfigModel(BaseModel):
    model_config = {
        'alias_generator': drop_config_suffix
    }


# This is a simple regex which is not by any means exhaustive but should cover gross syntax errors.
VALID_DOMAIN_NAME = re.compile(r"^localhost$|^(?!-)([A-Za-z0-9-]+\.)+[A-Za-z]{2,6}$")


def is_valid_domain_name(domain_name: str):
    stripped = domain_name.strip()
    matches = VALID_DOMAIN_NAME.match(stripped)
    assert matches is not None
    return stripped


DomainName = Annotated[str, AfterValidator(is_valid_domain_name)]


class Host(BaseModel):
    address: IPvAnyAddress | DomainName


class ExperimentBuilder(Generic[TExperiment], ConfigModel):
    """:class:`ExperimentBuilders` can build real :class:`Experiment`s out of :class:`ConfigModel`s. """

    @abstractmethod
    def build(self) -> TExperiment:
        pass
