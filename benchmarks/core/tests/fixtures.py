import logging
from io import StringIO
from typing import Tuple, Generator

import pytest


@pytest.fixture
def mock_logger() -> Generator[Tuple[logging.Logger, StringIO], None, None]:
    output = StringIO()
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.INFO)
    for handler in logger.handlers:
        logger.removeHandler(handler)
    handler = logging.StreamHandler(output)
    logger.addHandler(handler)

    yield logger, output

    logger.removeHandler(handler)
    handler.close()
