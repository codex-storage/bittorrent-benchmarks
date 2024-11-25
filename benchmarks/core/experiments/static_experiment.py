from typing_extensions import Generic, List

from benchmarks.core.network import TInitialMetadata, TNetworkHandle, Node
from benchmarks.core.utils import ExperimentData


class StaticDisseminationExperiment(Generic[TNetworkHandle, TInitialMetadata]):
    def __init__(
            self,
            network: List[Node[TNetworkHandle, TInitialMetadata]],
            seeders: List[int],
            data: ExperimentData[TInitialMetadata],
    ):
        self.nodes = network
        self.seeders = seeders
        self.data = data

    def run(self):
        seeders, leechers = (
            [
                self.nodes[i]
                for i in self.seeders
            ],
            [
                self.nodes[i]
                for i in range(0, len(self.nodes))
                if i not in self.seeders
            ]
        )

        with self.data as (meta, data):
            handle = meta
            for node in seeders:
                handle = node.seed(data, handle)

            handles = [node.leech(handle) for node in leechers]
            for handle in handles:
                handle.await_for_completion()
