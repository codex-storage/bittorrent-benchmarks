from ipaddress import IPv4Address, IPv6Address

import pytest
from pydantic import TypeAdapter, ValidationError

from benchmarks.core.pydantic import DomainName, Host


def test_should_parse_ipv4_address():
    h = TypeAdapter(Host).validate_strings('192.168.1.1')
    assert h == IPv4Address('192.168.1.1')


def test_should_parse_ipv6_address():
    h = TypeAdapter(Host).validate_strings('2001:0000:130F:0000:0000:09C0:876A:130B')
    assert h == IPv6Address('2001:0000:130F:0000:0000:09C0:876A:130B')


def test_should_parse_simple_dns_names():
    h = TypeAdapter(Host).validate_strings('node-1.local.svc')
    assert h == DomainName('node-1.local.svc')


def test_should_parse_localhost():
    h = TypeAdapter(Host).validate_strings('localhost')
    assert h == DomainName('localhost')


def test_should_return_correct_string_representation_for_addresses():
    h = TypeAdapter(Host).validate_strings('localhost')
    assert h == DomainName('localhost')

    h = TypeAdapter(Host).validate_strings('192.168.1.1')
    assert h == IPv4Address('192.168.1.1')


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
            TypeAdapter(Host).validate_strings(invalid_name)
