from itertools import islice
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field, model_validator
from torrentool.torrent import Torrent

from benchmarks.core.experiments.static_experiment import StaticDisseminationExperiment
from benchmarks.core.utils import sample
from benchmarks.deluge.config.host import Host
from benchmarks.deluge.deluge_node import DelugeMeta, DelugeNode as RealDelugeNode


class DelugeNode(BaseModel):
    address: Host
    daemon_port: int
    listen_ports: list[int] = Field(min_length=2, max_length=2)


class DelugeNodeSet(BaseModel):
    network_size: int = Field(gt=2)
    address: str
    daemon_port: int
    listen_ports: list[int] = Field(min_length=2, max_length=2)
    nodes: List[DelugeNode] = []

    @model_validator(mode='after')
    def expand_nodes(self):
        self.nodes = [
            DelugeNode(
                address=Host(address=self.address.format(node_index=str(i))),
                daemon_port=self.daemon_port,
                listen_ports=self.listen_ports,
            )
            for i in range(1, self.network_size + 1)
        ]


class DelugeExperiment(BaseModel):
    file_size: int = Field(gt=0)
    repetitions: int = Field(gt=0)
    seeders: int = Field(gt=0)
    shared_volume_path: Path
    nodes: List[DelugeNode] | DelugeNodeSet

    def build(self) -> StaticDisseminationExperiment[Torrent, DelugeMeta]:
        return StaticDisseminationExperiment(
            network=[
                RealDelugeNode(
                    name=f'deluge-{i}',
                    volume=self.shared_volume_path / f'deluge-{i}',
                    daemon_port=node.daemon_port,
                    daemon_address=node.address,
                )
                for i, node in enumerate(self.nodes)
            ],
            seeders=list(islice(sample(len(self.nodes)), self.seeders)),
            data=self.data
        )
