from io import StringIO

from benchmarks.deluge.config.deluge import DelugeNodeSet, DelugeNode
from benchmarks.deluge.config.host import Host


def test_should_expand_node_sets_into_simple_nodes():
    nodeset = DelugeNodeSet(
        address='deluge-{node_index}.local.svc',
        network_size=4,
        daemon_port=6080,
        listen_ports=[6081, 6082]
    )

    assert nodeset.nodes == [
        DelugeNode(
            address=Host(address='deluge-1.local.svc'),
            daemon_port=6080,
            listen_ports=[6081, 6082],
        ),
        DelugeNode(
            address=Host(address='deluge-2.local.svc'),
            daemon_port=6080,
            listen_ports=[6081, 6082],
        ),
        DelugeNode(
            address=Host(address='deluge-3.local.svc'),
            daemon_port=6080,
            listen_ports=[6081, 6082],
        ),
        DelugeNode(
            address=Host(address='deluge-4.local.svc'),
            daemon_port=6080,
            listen_ports=[6081, 6082],
        ),
    ]
