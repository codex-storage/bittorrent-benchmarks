from typing_extensions import Generic

from benchmarks.core.network import FileSharingNetwork, TNode
from benchmarks.core.utils import Sampler, DataGenerator


class StaticDisseminationExperiment(Generic[TNode]):
    def __init__(
            self,
            network: FileSharingNetwork[TNode],
            seeders: int,
            sampler: Sampler,
            generator: DataGenerator
    ):
        self.network = network
        self.sampler = sampler
        self.generate_data = generator
        self.seeders = seeders

    def run(self):
        sample = self.sampler(len(self.network.nodes))
        seeder_idx = [next(sample) for _ in range(0, self.seeders)]
        seeders, leechers = (
            [self.network.nodes[i] for i in seeder_idx],
            [self.network.nodes[i] for i in range(0, len(self.network.nodes)) if i not in seeder_idx]
        )

        data = self.generate_data()
        handle = None

        for node in seeders:
            handle = node.seed(data, handle)

        for node in leechers:
            node.leech(handle)
