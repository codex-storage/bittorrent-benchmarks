import logging
from multiprocessing.pool import ThreadPool
from time import sleep
from typing import Sequence, Optional

from typing_extensions import Generic, List, Tuple

from benchmarks.core.experiments.experiments import ExperimentWithLifecycle
from benchmarks.core.network import (
    TInitialMetadata,
    TNetworkHandle,
    Node,
    DownloadHandle,
)
from benchmarks.logging.logging import RequestEvent, RequestEventType

logger = logging.getLogger(__name__)


class StaticDisseminationExperiment(
    Generic[TNetworkHandle, TInitialMetadata], ExperimentWithLifecycle
):
    def __init__(
        self,
        network: Sequence[Node[TNetworkHandle, TInitialMetadata]],
        seeders: List[int],
        meta: TInitialMetadata,
        file_size: int,
        seed: int,
        concurrency: Optional[int] = None,
        logging_cooldown: int = 0,
    ) -> None:
        self.nodes = network
        self.seeders = seeders
        self.meta = meta
        self.file_size = file_size
        self.seed = seed

        self._pool = ThreadPool(
            processes=len(network) - len(seeders)
            if concurrency is None
            else concurrency
        )
        self._cid: Optional[TNetworkHandle] = None
        self.logging_cooldown = logging_cooldown

    def setup(self):
        pass

    def do_run(self, run: int = 0):
        seeders, leechers = self._split_nodes()

        logger.info(
            "Running experiment with %d seeders and %d leechers",
            len(seeders),
            len(leechers),
        )

        for node in seeders:
            _log_request(node, "genseed", str(self.meta), RequestEventType.start)
            self._cid = node.genseed(self.file_size, self.seed, self.meta)
            _log_request(node, "genseed", str(self.meta), RequestEventType.end)

        assert self._cid is not None  # to please mypy

        logger.info(f"Setting up leechers: {[str(leecher) for leecher in leechers]}")

        def _leech(leecher):
            _log_request(leecher, "leech", str(self.meta), RequestEventType.start)
            download = leecher.leech(self._cid)
            _log_request(leecher, "leech", str(self.meta), RequestEventType.end)
            return download

        downloads = list(self._pool.imap_unordered(_leech, leechers))

        logger.info("Now waiting for downloads to complete")

        def _await_for_download(element: Tuple[int, DownloadHandle]) -> int:
            index, download = element
            if not download.await_for_completion():
                raise Exception(
                    f"Download ({index}, {str(download)}) did not complete in time."
                )
            return index

        for i in self._pool.imap_unordered(_await_for_download, enumerate(downloads)):
            logger.info("Download %d / %d completed", i + 1, len(downloads))

        # FIXME this is a hack to ensure that nodes get a chance to log their data before we
        #   run the teardown hook and remove the torrents.
        logger.info(f"Waiting for {self.logging_cooldown} seconds before teardown...")
        sleep(self.logging_cooldown)

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
