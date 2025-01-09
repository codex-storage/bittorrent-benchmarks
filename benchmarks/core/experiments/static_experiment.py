import logging
from multiprocessing.pool import ThreadPool
from typing import Sequence, Optional

from typing_extensions import Generic, List, Tuple

from benchmarks.core.experiments.experiments import ExperimentWithLifecycle
from benchmarks.logging.logging import RequestEvent, RequestEventType
from benchmarks.core.network import (
    TInitialMetadata,
    TNetworkHandle,
    Node,
    DownloadHandle,
)
from benchmarks.core.utils import ExperimentData

logger = logging.getLogger(__name__)


class StaticDisseminationExperiment(
    Generic[TNetworkHandle, TInitialMetadata], ExperimentWithLifecycle
):
    def __init__(
        self,
        network: Sequence[Node[TNetworkHandle, TInitialMetadata]],
        seeders: List[int],
        data: ExperimentData[TInitialMetadata],
        concurrency: Optional[int] = None,
    ) -> None:
        self.nodes = network
        self.seeders = seeders
        self.data = data
        self._pool = ThreadPool(
            processes=len(network) - len(seeders)
            if concurrency is None
            else concurrency
        )
        self._cid: Optional[TNetworkHandle] = None

    def setup(self):
        pass

    def do_run(self, run: int = 0):
        seeders, leechers = self._split_nodes()

        logger.info(
            "Running experiment with %d seeders and %d leechers",
            len(seeders),
            len(leechers),
        )

        with self.data as (meta, data):
            for node in seeders:
                _log_request(node, "seed", str(meta), RequestEventType.start)
                self._cid = node.seed(data, meta if self._cid is None else self._cid)
                _log_request(node, "seed", str(meta), RequestEventType.end)

            assert self._cid is not None  # to please mypy

            logger.info(
                f"Setting up leechers: {[str(leecher) for leecher in leechers]}"
            )

            def _leech(leecher):
                _log_request(leecher, "leech", str(meta), RequestEventType.start)
                download = leecher.leech(self._cid)
                _log_request(leecher, "leech", str(meta), RequestEventType.end)
                return download

            downloads = list(self._pool.imap_unordered(_leech, leechers))

            logger.info("Now waiting for downloads to complete")

            def _await_for_download(element: Tuple[int, DownloadHandle]) -> int:
                index, download = element
                download.await_for_completion()
                return index

            for i in self._pool.imap_unordered(
                _await_for_download, enumerate(downloads)
            ):
                logger.info("Download %d / %d completed", i + 1, len(downloads))

    def teardown(self, exception: Optional[Exception] = None):
        def _remove(element: Tuple[int, Node[TNetworkHandle, TInitialMetadata]]):
            index, node = element
            assert self._cid is not None  # to please mypy
            node.remove(self._cid)
            return index

        try:
            for i in self._pool.imap_unordered(_remove, enumerate(self.nodes)):
                logger.info("Node %d removed file", i + 1)
        finally:
            logger.info("Shut down thread pool.")
            self._pool.close()
            self._pool.join()
            logger.info("Done.")

    def _split_nodes(
        self,
    ) -> Tuple[
        List[Node[TNetworkHandle, TInitialMetadata]],
        List[Node[TNetworkHandle, TInitialMetadata]],
    ]:
        return [self.nodes[i] for i in self.seeders], [
            self.nodes[i] for i in range(0, len(self.nodes)) if i not in self.seeders
        ]


def _log_request(
    node: Node[TNetworkHandle, TInitialMetadata],
    name: str,
    request_id: str,
    event_type: RequestEventType,
):
    logger.info(
        RequestEvent(
            node="runner",
            destination=node.name,
            name=name,
            request_id=request_id,
            type=event_type,
        )
    )
