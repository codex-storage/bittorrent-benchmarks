import random
from itertools import islice
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field, model_validator, HttpUrl
from torrentool.torrent import Torrent
from urllib3.util import parse_url

from benchmarks.core.experiments.experiments import (
    ExperimentEnvironment,
    BoundExperiment,
    ExperimentBuilder,
)
from benchmarks.core.experiments.iterated_experiment import IteratedExperiment
from benchmarks.core.experiments.static_experiment import StaticDisseminationExperiment
from benchmarks.core.pydantic import Host
from benchmarks.core.utils.random import sample

from benchmarks.deluge.agent.client import DelugeAgentClient
from benchmarks.deluge.deluge_node import DelugeMeta, DelugeNode
from benchmarks.deluge.tracker import Tracker


class DelugeNodeConfig(BaseModel):
    name: str
    address: Host
    daemon_port: int
    listen_ports: list[int] = Field(min_length=2, max_length=2)
    agent_url: HttpUrl


class DelugeNodeSetConfig(BaseModel):
    network_size: int = Field(gt=1)
    name: str
    address: str
    daemon_port: int
    listen_ports: list[int] = Field(min_length=2, max_length=2)
    first_node_index: int = 1
    nodes: List[DelugeNodeConfig] = []
    agent_url: str

    @model_validator(mode="after")
    def expand_nodes(self):
        self.nodes = [
            DelugeNodeConfig(
                name=self.name.format(node_index=str(i)),
                address=self.address.format(node_index=str(i)),
                daemon_port=self.daemon_port,
                listen_ports=self.listen_ports,
                agent_url=self.agent_url.format(node_index=str(i)),
            )
            for i in range(
                self.first_node_index, self.first_node_index + self.network_size
            )
        ]
        return self


DelugeDisseminationExperiment = IteratedExperiment[
    BoundExperiment[StaticDisseminationExperiment[Torrent, DelugeMeta]]
]


class DelugeExperimentConfig(ExperimentBuilder[DelugeDisseminationExperiment]):
    experiment_set_id: str = Field(
        description="Identifies the group of experiment repetitions", default="unnamed"
    )
    seeder_sets: int = Field(
        gt=0, default=1, description="Number of distinct seeder sets to experiment with"
    )
    seeders: int = Field(gt=0, description="Number of seeders per seeder set")

    repetitions: int = Field(
        gt=0, description="How many experiment repetitions to run for each seeder set"
    )
    file_size: int = Field(gt=0, description="File size, in bytes")

    shared_volume_path: Path = Field(
        description="Path to the volume shared between clients and experiment runner"
    )
    tracker_announce_url: HttpUrl = Field(
        description="URL to the tracker announce endpoint"
    )

    nodes: List[DelugeNodeConfig] | DelugeNodeSetConfig = Field(
        description="Configuration for the nodes that make up the network"
    )

    logging_cooldown: int = Field(
        gt=0,
        default=0,
        description="Time to wait after the last download completes before tearing down the experiment.",
    )

    def build(self) -> DelugeDisseminationExperiment:
        nodes_specs = (
            self.nodes.nodes
            if isinstance(self.nodes, DelugeNodeSetConfig)
            else self.nodes
        )

        agents = [
            DelugeAgentClient(parse_url(str(node_spec.agent_url)))
            for node_spec in nodes_specs
        ]

        network = [
            DelugeNode(
                name=node_spec.name,
                volume=self.shared_volume_path,
                daemon_port=node_spec.daemon_port,
                daemon_address=str(node_spec.address),
                agent=agents[i],
            )
            for i, node_spec in enumerate(nodes_specs)
        ]

        tracker = Tracker(parse_url(str(self.tracker_announce_url)))

        env = ExperimentEnvironment(
            components=network + agents + [tracker],
            ping_max=10,
            polling_interval=0.5,
        )

        def repetitions():
            for seeder_set in range(self.seeder_sets):
                seeders = list(islice(sample(len(network)), self.seeders))
                for experiment_run in range(self.repetitions):
                    yield env.bind(
                        StaticDisseminationExperiment(
                            network=network,
                            seeders=seeders,
                            file_size=self.file_size,
                            seed=random.randint(0, 2**16),
                            meta=DelugeMeta(
                                f"dataset-{seeder_set}-{experiment_run}",
                                announce_url=tracker.announce_url,
                            ),
                            logging_cooldown=self.logging_cooldown,
                        )
                    )

        return IteratedExperiment(
            repetitions(), experiment_set_id=self.experiment_set_id
        )
