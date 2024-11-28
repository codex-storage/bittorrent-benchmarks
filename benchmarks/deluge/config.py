from itertools import islice
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field, model_validator, HttpUrl
from torrentool.torrent import Torrent
from urllib3.util import parse_url

from benchmarks.core.config import Host, ExperimentBuilder
from benchmarks.core.experiments.experiments import IteratedExperiment
from benchmarks.core.experiments.static_experiment import StaticDisseminationExperiment
from benchmarks.core.utils import sample, RandomTempData
from benchmarks.deluge.deluge_node import DelugeMeta, DelugeNode


class DelugeNodeConfig(BaseModel):
    address: Host
    daemon_port: int
    listen_ports: list[int] = Field(min_length=2, max_length=2)


class DelugeNodeSetConfig(BaseModel):
    network_size: int = Field(gt=2)
    address: str
    daemon_port: int
    listen_ports: list[int] = Field(min_length=2, max_length=2)
    nodes: List[DelugeNodeConfig] = []

    @model_validator(mode='after')
    def expand_nodes(self):
        self.nodes = [
            DelugeNodeConfig(
                address=self.address.format(node_index=str(i)),
                daemon_port=self.daemon_port,
                listen_ports=self.listen_ports,
            )
            for i in range(1, self.network_size + 1)
        ]
        return self


DelugeDisseminationExperiment = IteratedExperiment[StaticDisseminationExperiment[Torrent, DelugeMeta]]


class DelugeExperimentConfig(ExperimentBuilder[DelugeDisseminationExperiment]):
    repetitions: int = Field(gt=0)
    file_size: int = Field(gt=0)
    seeders: int = Field(gt=0)
    shared_volume_path: Path
    tracker_announce_url: HttpUrl
    nodes: List[DelugeNodeConfig] | DelugeNodeSetConfig

    def build(self) -> DelugeDisseminationExperiment:
        nodes = self.nodes.nodes if isinstance(self.nodes, DelugeNodeSetConfig) else self.nodes
        repetitions = (
            StaticDisseminationExperiment(
                network=[
                    DelugeNode(
                        name=f'deluge-{i + 1}',
                        volume=self.shared_volume_path,
                        daemon_port=node.daemon_port,
                        daemon_address=str(node.address),
                    )
                    for i, node in enumerate(nodes)
                ],
                seeders=list(islice(sample(len(nodes)), self.seeders)),
                data=RandomTempData(size=self.file_size,
                                    meta=DelugeMeta(f'dataset-{experiment_run}',
                                                    announce_url=parse_url(str(self.tracker_announce_url))))
            )
            for experiment_run in range(self.repetitions)
        )

        return IteratedExperiment(repetitions)
