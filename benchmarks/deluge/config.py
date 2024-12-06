from itertools import islice
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field, model_validator, HttpUrl
from torrentool.torrent import Torrent
from urllib3.util import parse_url

from benchmarks.core.config import Host, ExperimentBuilder
from benchmarks.core.experiments.experiments import IteratedExperiment, ExperimentEnvironment, Experiment, \
    BoundExperiment
from benchmarks.core.experiments.static_experiment import StaticDisseminationExperiment
from benchmarks.core.utils import sample, RandomTempData
from benchmarks.deluge.deluge_node import DelugeMeta, DelugeNode
from benchmarks.deluge.tracker import Tracker


class DelugeNodeConfig(BaseModel):
    name: str
    address: Host
    daemon_port: int
    listen_ports: list[int] = Field(min_length=2, max_length=2)


class DelugeNodeSetConfig(BaseModel):
    network_size: int = Field(gt=1)
    name: str
    address: str
    daemon_port: int
    listen_ports: list[int] = Field(min_length=2, max_length=2)
    first_node_index: int = 1
    nodes: List[DelugeNodeConfig] = []

    @model_validator(mode='after')
    def expand_nodes(self):
        self.nodes = [
            DelugeNodeConfig(
                name=self.name.format(node_index=str(i)),
                address=self.address.format(node_index=str(i)),
                daemon_port=self.daemon_port,
                listen_ports=self.listen_ports,
            )
            for i in range(self.first_node_index, self.first_node_index + self.network_size)
        ]
        return self


DelugeDisseminationExperiment = IteratedExperiment[BoundExperiment[StaticDisseminationExperiment[Torrent, DelugeMeta]]]


class DelugeExperimentConfig(ExperimentBuilder[DelugeDisseminationExperiment]):
    repetitions: int = Field(gt=0)
    file_size: int = Field(gt=0)
    seeders: int = Field(gt=0)
    shared_volume_path: Path
    tracker_announce_url: HttpUrl
    nodes: List[DelugeNodeConfig] | DelugeNodeSetConfig

    def build(self) -> DelugeDisseminationExperiment:
        nodes_specs = self.nodes.nodes if isinstance(self.nodes, DelugeNodeSetConfig) else self.nodes

        network = [
            DelugeNode(
                name=node_spec.name,
                volume=self.shared_volume_path,
                daemon_port=node_spec.daemon_port,
                daemon_address=str(node_spec.address),
            )
            for i, node_spec in enumerate(nodes_specs)
        ]

        tracker = Tracker(parse_url(str(self.tracker_announce_url)))

        env = ExperimentEnvironment(
            components=network + [tracker],
            polling_interval=0.5,
        )

        repetitions = (
            env.bind(StaticDisseminationExperiment(
                network=network,
                seeders=list(islice(sample(len(network)), self.seeders)),
                data=RandomTempData(size=self.file_size,
                                    meta=DelugeMeta(f'dataset-{experiment_run}',
                                                    announce_url=tracker.announce_url))
            ))
            for experiment_run in range(self.repetitions)
        )

        return IteratedExperiment(repetitions)
