from io import StringIO
from unittest.mock import patch

import yaml

from benchmarks.core.config import Host
from benchmarks.deluge.config import DelugeNodeSetConfig, DelugeNodeConfig, DelugeExperimentConfig


def test_should_expand_node_sets_into_simple_nodes():
    nodeset = DelugeNodeSetConfig(
        address='deluge-{node_index}.local.svc',
        network_size=4,
        daemon_port=6080,
        listen_ports=[6081, 6082]
    )

    assert nodeset.nodes == [
        DelugeNodeConfig(
            address=Host(address='deluge-1.local.svc'),
            daemon_port=6080,
            listen_ports=[6081, 6082],
        ),
        DelugeNodeConfig(
            address=Host(address='deluge-2.local.svc'),
            daemon_port=6080,
            listen_ports=[6081, 6082],
        ),
        DelugeNodeConfig(
            address=Host(address='deluge-3.local.svc'),
            daemon_port=6080,
            listen_ports=[6081, 6082],
        ),
        DelugeNodeConfig(
            address=Host(address='deluge-4.local.svc'),
            daemon_port=6080,
            listen_ports=[6081, 6082],
        ),
    ]


def test_should_build_experiment_from_config():
    config_file = StringIO("""
    deluge_experiment:
      seeders: 3
      tracker_announce_url: http://localhost:2020/announce
      file_size: 1024
      shared_volume_path: /var/lib/deluge

      nodes:
        network_size: 10
        address: 'node-{node_index}.deluge.codexbenchmarks.svc.cluster.local'
        daemon_port: 6890
        listen_ports: [ 6891, 6892 ]
    """)

    config = DelugeExperimentConfig.model_validate(yaml.safe_load(config_file)['deluge_experiment'])

    # Need to patch mkdir, or we'll try to actually create the folder when DelugeNode gets initialized.
    with patch('pathlib.Path.mkdir'):
        experiment = config.build()


    assert len(experiment.nodes) == 10


