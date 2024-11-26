import re
from typing import Annotated

from pydantic import BaseModel, StringConstraints, IPvAnyAddress, AfterValidator

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
