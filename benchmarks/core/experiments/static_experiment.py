from typing_extensions import Generic, List

from benchmarks.core.network import TInitialMetadata, TNetworkHandle, Node
from benchmarks.core.utils import Sampler, DataGenerator, DataHandle
from benchmarks.core.experiments.experiments import Experiment, RunnableExperiment


class _RunnableSDE(RunnableExperiment, Generic[TNetworkHandle, TInitialMetadata]):
    def __init__(
            self,
            network: List[Node[TNetworkHandle, TInitialMetadata]],
            seeders: List[int],
            data_handle: DataHandle[TInitialMetadata],
    ):
        self.nodes = network
        self.seeders = seeders
        self.data_handle = data_handle

    def _run(self):
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

        handle = self.data_handle.meta
        for node in seeders:
            handle = node.seed(self.data_handle.data, handle)

        handles = [node.leech(handle) for node in leechers]
        for handle in handles:
            handle.await_for_completion()

    def teardown(self):
        self.data_handle.cleanup()


class StaticDisseminationExperiment(Experiment[_RunnableSDE[TNetworkHandle, TInitialMetadata]]):
    def __init__(
            self,
            network: List[Node[TNetworkHandle, TInitialMetadata]],
            seeders: int,
            sampler: Sampler,
            generator: DataGenerator[TInitialMetadata],
    ):
        self.nodes = network
        self.sampler = sampler
        self.generator = generator
        self.seeders = seeders

    def setup(self) -> _RunnableSDE[TNetworkHandle, TInitialMetadata]:
        sample = self.sampler(len(self.nodes))
        return _RunnableSDE(
            network=self.nodes,
            seeders=[next(sample) for _ in range(0, self.seeders)],
            data_handle=self.generator.generate()
        )
