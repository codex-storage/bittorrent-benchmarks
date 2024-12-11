import os
from io import StringIO
from typing import cast

import yaml

from benchmarks.core.config import ConfigParser
from benchmarks.core.pydantic import SnakeCaseModel


class Root1(SnakeCaseModel):
    index: int


class Root2(SnakeCaseModel):
    name: str


def test_should_parse_multiple_roots():
    config_file = StringIO("""
    root1:
      index: 1
    
    root2: 
      name: "root2"
    """)

    parser = ConfigParser()

    parser.register(Root1)
    parser.register(Root2)

    conf = parser.parse(yaml.safe_load(config_file))

    assert cast(Root1, conf['root1']).index == 1
    assert cast(Root2, conf['root2']).name == 'root2'


def test_should_expand_env_vars_when_fed_a_config_file():
    config_file = StringIO("""
    root1:
      index: ${BTB_MY_INDEX}
    root2:
      name: "My name is ${BTB_NAME}"
    """)

    os.environ['BTB_MY_INDEX'] = '10'
    os.environ['BTB_NAME'] = 'John Doe'

    parser = ConfigParser()
    parser.register(Root1)
    parser.register(Root2)

    conf = parser.parse(config_file)
    assert cast(Root1, conf['root1']).index == 10
    assert cast(Root2, conf['root2']).name == 'My name is John Doe'
