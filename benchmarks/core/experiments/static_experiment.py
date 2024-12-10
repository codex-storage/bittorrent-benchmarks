import logging
from multiprocessing.pool import ThreadPool
from typing import Sequence

from typing_extensions import Generic, List, Tuple

from benchmarks.core.experiments.experiments import Experiment
from benchmarks.core.network import TInitialMetadata, TNetworkHandle, Node, DownloadHandle
from benchmarks.core.utils import ExperimentData

logger = logging.getLogger(__name__)


class StaticDisseminationExperiment(Generic[TNetworkHandle, TInitialMetadata], Experiment):
    def __init__(
            self,
            network: Sequence[Node[TNetworkHandle, TInitialMetadata]],
            seeders: List[int],
            data: ExperimentData[TInitialMetadata],
    ):
        self.nodes = network
        self.seeders = seeders
        self.data = data
        self._pool = ThreadPool(processes=len(network) - len(seeders))

    def run(self, run: int = 0):
        seeders, leechers = self._split_nodes()

        logger.info('Running experiment with %d seeders and %d leechers',
                    len(seeders), len(leechers))

        with self.data as (meta, data):
            cid = None
            for node in seeders:
                logger.info(f'Seeding data: {str(node)}')
                cid = node.seed(data, meta if cid is None else cid)

            assert cid is not None  # to please mypy

            logger.info(f'Setting up leechers: {[str(leecher) for leecher in leechers]}')
            downloads = list(self._pool.imap_unordered(lambda leecher: leecher.leech(cid), leechers))

            logger.info('Now waiting for downloads to complete')

            def _await_for_download(element: Tuple[int, DownloadHandle]) -> int:
                index, download = element
                download.await_for_completion()
                return index

            for i in self._pool.imap_unordered(_await_for_download, enumerate(downloads)):
                logger.info('Download %d / %d completed', i + 1, len(downloads))

            logger.info('Shut down thread pool.')
            self._pool.close()
            self._pool.join()
            logger.info('Done.')

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
