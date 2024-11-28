from typing_extensions import Generic, List

from benchmarks.core.experiments.experiments import Experiment
from benchmarks.core.network import TInitialMetadata, TNetworkHandle, Node
from benchmarks.core.utils import ExperimentData


class StaticDisseminationExperiment(Generic[TNetworkHandle, TInitialMetadata], Experiment):
    def __init__(
            self,
            network: List[Node[TNetworkHandle, TInitialMetadata]],
            seeders: List[int],
            data: ExperimentData[TInitialMetadata],
    ):
        self.nodes = network
        self.seeders = seeders
        self.data = data

    def run(self, run: int = 0):
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
            meta_or_cid = meta
            for node in seeders:
                meta_or_cid = node.seed(data, meta_or_cid)

            downloads = [node.leech(meta_or_cid) for node in leechers]
            for download in downloads:
                download.await_for_completion()
