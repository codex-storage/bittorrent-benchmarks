import logging
from multiprocessing.pool import ThreadPool
from typing import Sequence, Optional

from typing_extensions import Generic, List, Tuple

from benchmarks.core.experiments.experiments import Experiment
from benchmarks.core.logging import RequestEvent, RequestEventType
from benchmarks.core.network import TInitialMetadata, TNetworkHandle, Node, DownloadHandle
from benchmarks.core.utils import ExperimentData

logger = logging.getLogger(__name__)


class StaticDisseminationExperiment(Generic[TNetworkHandle, TInitialMetadata], Experiment):
    def __init__(
            self,
            network: Sequence[Node[TNetworkHandle, TInitialMetadata]],
            seeders: List[int],
            data: ExperimentData[TInitialMetadata],
            concurrency: Optional[int] = None
    ):
        self.nodes = network
        self.seeders = seeders
        self.data = data
        self._pool = ThreadPool(processes=len(network) - len(seeders) if concurrency is None else concurrency)

    def run(self, run: int = 0):
        seeders, leechers = self._split_nodes()

        logger.info('Running experiment with %d seeders and %d leechers',
                    len(seeders), len(leechers))

        with self.data as (meta, data):
            cid = None
            for node in seeders:
                logger.info(RequestEvent(
                    node='runner',
                    destination=node.name,
                    name='seed',
                    request_id=str(meta),
                    type=RequestEventType.start
                ))
                cid = node.seed(data, meta if cid is None else cid)
                logger.info(RequestEvent(
                    node='runner',
                    destination=node.name,
                    name='seed',
                    request_id=str(meta),
                    type=RequestEventType.end
                ))

            assert cid is not None  # to please mypy

            logger.info(f'Setting up leechers: {[str(leecher) for leecher in leechers]}')

            def _leech(leecher):
                logger.info(RequestEvent(
                    node='runner',
                    destination=leecher.name,
                    name='leech',
                    request_id=str(meta),
                    type=RequestEventType.start
                ))
                download = leecher.leech(cid)
                logger.info(RequestEvent(
                    node='runner',
                    destination=leecher.name,
                    name='leech',
                    request_id=str(meta),
                    type=RequestEventType.end
                ))
                return download

            downloads = list(self._pool.imap_unordered(_leech, leechers))

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
