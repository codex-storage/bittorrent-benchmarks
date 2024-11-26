from ipaddress import IPv4Address, IPv6Address

import pytest
from pydantic import ValidationError

from benchmarks.deluge.config.host import Host, DomainName


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
