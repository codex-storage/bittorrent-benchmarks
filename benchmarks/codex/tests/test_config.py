from io import StringIO
from typing import cast

import yaml
from urllib3.util import parse_url

from benchmarks.codex.codex_node import CodexNode
from benchmarks.codex.config import (
    CodexNodeConfig,
    CodexNodeSetConfig,
    CodexExperimentConfig,
)


def test_should_expand_node_sets_into_simple_nodes():
    nodeset = CodexNodeSetConfig(
        network_size=3,
        first_node_index=0,
        name="codex-{node_index}",
        address="codex-{node_index}.local.svc",
        disc_port=6890,
        api_port=6891,
        agent_url="http://codex-{node_index}.local.svc:9000",
    )

    assert nodeset.nodes == [
        CodexNodeConfig(
            name="codex-0",
            address="codex-0.local.svc",
            disc_port=6890,
            api_port=6891,
            agent_url="http://codex-0.local.svc:9000",
        ),
        CodexNodeConfig(
            name="codex-1",
            address="codex-1.local.svc",
            disc_port=6890,
            api_port=6891,
            agent_url="http://codex-1.local.svc:9000",
        ),
        CodexNodeConfig(
            name="codex-2",
            address="codex-2.local.svc",
            disc_port=6890,
            api_port=6891,
            agent_url="http://codex-2.local.svc:9000",
        ),
    ]


def test_should_build_experiment_from_config():
    config_file = StringIO("""
    codex_experiment:
      repetitions: 3
      seeders: 3
      seeder_sets: 3
      file_size: 1024
      logging_cooldown: 10

      nodes:
        network_size: 5
        first_node_index: 0
        name: "codex-nodes-{node_index}"
        address: "codex-nodes-{node_index}.codex-nodes-service.codex-benchmarks.svc.cluster.local"
        disc_port: 6890
        api_port: 6891
        agent_url: "http://codex-nodes-{node_index}.codex-nodes-service.codex-benchmarks.svc.cluster.local:9000/"
    """)

    config = CodexExperimentConfig.model_validate(
        yaml.safe_load(config_file)["codex_experiment"]
    )

    experiment = config.build()
    repetitions = list(experiment.experiments)

    assert len(repetitions) == 9
    assert len(repetitions[0].experiment.nodes) == 5
    assert cast(
        CodexNode, repetitions[0].experiment.nodes[4]
    ).codex_api_url == parse_url(
        "http://codex-nodes-4.codex-nodes-service.codex-benchmarks.svc.cluster.local:6891"
    )
