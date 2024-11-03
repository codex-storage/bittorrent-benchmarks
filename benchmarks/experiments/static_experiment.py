from typing_extensions import Generic, List

from benchmarks.core.network import TInitialMetadata, TNetworkHandle, Node
from benchmarks.core.utils import Sampler, DataGenerator


class StaticDisseminationExperiment(Generic[TNetworkHandle, TInitialMetadata]):
    def __init__(
            self,
            network: List[Node[TNetworkHandle, TInitialMetadata]],
            seeders: int,
            sampler: Sampler,
            generator: DataGenerator
    ):
        self.nodes = network
        self.sampler = sampler
        self.generate_data = generator
        self.seeders = seeders

    def run(self):
        sample = self.sampler(len(self.nodes))
        seeder_indexes = [next(sample) for _ in range(0, self.seeders)]
        seeders, leechers = (
            [
                self.nodes[i]
                for i in seeder_indexes
            ],
            [
                self.nodes[i]
                for i in range(0, len(self.nodes))
                if i not in seeder_indexes
            ]
        )

        meta, data = self.generate_data()

        handle = meta
        for node in seeders:
            handle = node.seed(data, handle)

        handles = [node.leech(handle) for node in leechers]
        for handle in handles:
            handle.await_for_completion()
