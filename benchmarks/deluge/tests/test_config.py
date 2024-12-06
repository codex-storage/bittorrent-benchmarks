from io import StringIO
from typing import cast
from unittest.mock import patch

import yaml

from benchmarks.deluge.config import DelugeNodeSetConfig, DelugeNodeConfig, DelugeExperimentConfig
from benchmarks.deluge.deluge_node import DelugeNode


def test_should_expand_node_sets_into_simple_nodes():
    nodeset = DelugeNodeSetConfig(
        name='custom-{node_index}',
        address='deluge-{node_index}.local.svc',
        network_size=4,
        daemon_port=6080,
        listen_ports=[6081, 6082]
    )

    assert nodeset.nodes == [
        DelugeNodeConfig(
            name='custom-1',
            address='deluge-1.local.svc',
            daemon_port=6080,
            listen_ports=[6081, 6082],
        ),
        DelugeNodeConfig(
            name='custom-2',
            address='deluge-2.local.svc',
            daemon_port=6080,
            listen_ports=[6081, 6082],
        ),
        DelugeNodeConfig(
            name='custom-3',
            address='deluge-3.local.svc',
            daemon_port=6080,
            listen_ports=[6081, 6082],
        ),
        DelugeNodeConfig(
            name='custom-4',
            address='deluge-4.local.svc',
            daemon_port=6080,
            listen_ports=[6081, 6082],
        ),
    ]

def test_should_respect_first_node_index():
    nodeset = DelugeNodeSetConfig(
        name='deluge-{node_index}',
        address='deluge-{node_index}.local.svc',
        network_size=2,
        daemon_port=6080,
        listen_ports=[6081, 6082],
        first_node_index=5
    )

    assert nodeset.nodes == [
        DelugeNodeConfig(
            name='deluge-5',
            address='deluge-5.local.svc',
            daemon_port=6080,
            listen_ports=[6081, 6082],
        ),
        DelugeNodeConfig(
            name='deluge-6',
            address='deluge-6.local.svc',
            daemon_port=6080,
            listen_ports=[6081, 6082],
        ),
    ]

def test_should_build_experiment_from_config():
    config_file = StringIO("""
    deluge_experiment:
      repetitions: 3
      seeders: 3
      tracker_announce_url: http://localhost:2020/announce
      file_size: 1024
      shared_volume_path: /var/lib/deluge

      nodes:
        network_size: 10
        name: 'deluge-{node_index}'
        address: 'node-{node_index}.deluge.codexbenchmarks.svc.cluster.local'
        daemon_port: 6890
        listen_ports: [ 6891, 6892 ]
    """)

    config = DelugeExperimentConfig.model_validate(yaml.safe_load(config_file)['deluge_experiment'])

    # Need to patch mkdir, or we'll try to actually create the folder when DelugeNode gets initialized.
    with patch('pathlib.Path.mkdir'):
        experiment = config.build()
        repetitions = list(experiment.experiments)

    assert len(repetitions) == 3

    assert len(repetitions[0].experiment.nodes) == 10
    assert cast(DelugeNode, repetitions[0].experiment.nodes[5]).daemon_args['port'] == 6890


