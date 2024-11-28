import os
from io import StringIO
from ipaddress import IPv4Address, IPv6Address
from typing import cast

import pytest
import yaml
from pydantic import ValidationError, BaseModel

from benchmarks.core.config import Host, DomainName, ConfigParser, ConfigModel


def test_should_parse_ipv4_address():
    h = Host(address='192.168.1.1')
    assert h.address == IPv4Address('192.168.1.1')


def test_should_parse_ipv6_address():
    h = Host(address='2001:0000:130F:0000:0000:09C0:876A:130B')
    assert h.address == IPv6Address('2001:0000:130F:0000:0000:09C0:876A:130B')


def test_should_parse_simple_dns_names():
    h = Host(address='node-1.local.svc')
    assert h.address == DomainName('node-1.local.svc')


def test_should_parse_localhost():
    h = Host(address='localhost')
    assert h.address == DomainName('localhost')


def test_should_return_correct_string_representation_for_addresses():
    h = Host(address='localhost')
    assert str(h.address) == 'localhost'

    h = Host(address='192.168.1.1')
    assert str(h.address) == '192.168.1.1'


def test_should_fail_invalid_names():
    invalid_names = [
        '-node-1.local.svc',
        'node-1.local..svc',
        'node-1.local.svc.',
        'node-1.local.reallylongsubdomain',
        'node-1.local.s-dash',
        'notlocalhost',
    ]

    for invalid_name in invalid_names:
        with pytest.raises(ValidationError):
            Host(address=invalid_name)


class Root1(ConfigModel):
    index: int


class Root2(ConfigModel):
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
