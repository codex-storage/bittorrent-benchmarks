import re
from typing import Annotated

from pydantic import BaseModel, AfterValidator, IPvAnyAddress


def drop_config_suffix(name: str) -> str:
    return name[:-6] if name.endswith("Config") else name


def to_snake_case(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


class SnakeCaseModel(BaseModel):
    model_config = {"alias_generator": lambda x: to_snake_case(drop_config_suffix(x))}

    @classmethod
    def alias(cls):
        return cls.model_config["alias_generator"](cls.__name__)


# This is a simple regex which is not by any means exhaustive but should cover gross syntax errors.
VALID_DOMAIN_NAME = re.compile(r"^localhost$|^(?!-)([A-Za-z0-9-]+\.)+[A-Za-z]{2,6}$")


def is_valid_domain_name(domain_name: str):
    stripped = domain_name.strip()
    matches = VALID_DOMAIN_NAME.match(stripped)
    assert matches is not None
    return stripped


DomainName = Annotated[str, AfterValidator(is_valid_domain_name)]

type Host = IPvAnyAddress | DomainName
