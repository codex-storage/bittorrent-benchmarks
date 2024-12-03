from typing_extensions import Generic, List, Tuple

from benchmarks.core.experiments.experiments import Experiment
from benchmarks.core.network import TInitialMetadata, TNetworkHandle, Node
from benchmarks.core.utils import ExperimentData

import logging

logger = logging.getLogger(__name__)


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
        seeders, leechers = self._split_nodes()

        logger.info('Running experiment with %d seeders and %d leechers',
                    len(seeders), len(leechers))

        with self.data as (meta, data):
            cid = None
            logger.info('Seeding data')
            for node in seeders:
                cid = node.seed(data, meta if cid is None else cid)

            assert cid is not None  # to please mypy

            logger.info('Setting up leechers')
            downloads = [node.leech(cid) for node in leechers]

            logger.info('Now waiting for downloads to complete')
            for i, download in enumerate(downloads):
                download.await_for_completion()
                logger.info('Download %d / %d completed', i + 1, len(downloads))

    def _split_nodes(self) -> Tuple[
        List[Node[TNetworkHandle, TInitialMetadata]],
        List[Node[TNetworkHandle, TInitialMetadata]]
    ]:
        return [
            self.nodes[i]
            for i in self.seeders
        ], [
            self.nodes[i]
            for i in range(0, len(self.nodes))
            if i not in self.seeders
        ]
