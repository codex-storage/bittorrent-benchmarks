import asyncio
import logging
import time
from asyncio import Task
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, Dict

from aiohttp import ClientTimeout

from benchmarks.codex.client.async_client import AsyncCodexClient, DownloadStatus
from benchmarks.codex.client.common import Cid
from benchmarks.codex.client.common import Manifest
from benchmarks.core.utils.random import random_data
from benchmarks.logging.logging import DownloadMetric

STATUS_BACKOFF = 2.0
PROGRESS_TIMEOUT = 120

logger = logging.getLogger(__name__)


class DownloadHandle:
    def __init__(
        self,
        parent: "CodexAgent",
        manifest: Manifest,
        log_increment: float = 0.01,
        status_backoff: float = STATUS_BACKOFF,
        progress_timeout: float = PROGRESS_TIMEOUT,
    ):
        self.parent = parent
        self.manifest = manifest
        self.log_increment = log_increment
        self.download_task: Optional[Task[None]] = None
        self.status_backoff = status_backoff
        self.progress_timeout = progress_timeout
        self._progress = DownloadStatus(downloaded=0, total=manifest.block_count)

    def begin_download(self) -> Task:
        self.download_task = asyncio.create_task(self._download_loop())
        return self.download_task

    async def _download_loop(self):
        step_size = max(1, int(self.manifest.block_count * self.log_increment))

        download_id = await self.parent.client.download(
            self.manifest,
            timeout=ClientTimeout(
                total=None,
                sock_connect=30,
            ),
        )

        logger.info(f"Start download monitoring loop for {download_id}")

        current_step = 0
        last_progress = time.time()
        while True:
            has_progress = False
            progress = await self.parent.client.download_status(download_id)
            self._publish_progress(progress)
            while current_step < (progress.downloaded / step_size):
                has_progress = True
                current_step += 1
                self._log_progress(current_step * step_size)

            if not has_progress:
                # Backs off for a bit if we haven't seen any progress.
                await asyncio.sleep(self.status_backoff)
            else:
                last_progress = time.time()

            if progress.is_complete():
                # If step_size is not a multiple of 1/log_increment, we have a trailing step for the
                # remainder.
                if current_step * step_size < self.manifest.block_count:
                    self._log_progress(current_step * step_size)
                break

            if time.time() - last_progress > self.progress_timeout:
                raise asyncio.TimeoutError(
                    f"Download made no progress in more than {self.progress_timeout} seconds"
                )

    def progress(self) -> DownloadStatus:
        return self._progress

    def _publish_progress(self, status: DownloadStatus):
        self._progress = DownloadStatus(
            downloaded=status.downloaded * self.manifest.blockSize,
            total=status.total * self.manifest.blockSize,
        )

    def _log_progress(self, downloaded: int):
        logger.info(
            DownloadMetric(
                dataset_name=self.manifest.filename,
                value=downloaded * self.manifest.blockSize,
                node=self.parent.node_id,
            )
        )


class CodexAgent:
    """:class:`CodexAgent` interacts with the Codex node locally through its REST API
    providing the higher-level API required by the benchmarking experiments."""

    def __init__(
        self,
        client: AsyncCodexClient,
        node_id: str = "unknown",
        status_backoff: float = STATUS_BACKOFF,
        progress_timeout: float = PROGRESS_TIMEOUT,
    ) -> None:
        self.client = client
        self.node_id = node_id
        self.ongoing_downloads: Dict[Cid, DownloadHandle] = {}
        self.status_backoff = status_backoff
        self.progress_timeout = progress_timeout

    async def create_dataset(
        self, name: str, size: int, seed: Optional[int]
    ) -> Manifest:
        """
        Creates a random dataset and uploads it to the Codex node.

        :param name: the name of the dataset to be created.
        :param size: the size of the dataset to be created, in bytes.
        :param seed: the seed to be used for generating the random dataset. Using the
            same seed will generate the exact same dataset.

        :return: the :class:`Manifest` block for the dataset.
        """
        with TemporaryDirectory() as td:
            data = Path(td) / "datafile.bin"

            with data.open(mode="wb") as outfile:
                random_data(size=size, outfile=outfile, seed=seed)

            with data.open(mode="rb") as infile:
                cid = await self.client.upload(
                    name=name, mime_type="application/octet-stream", content=infile
                )

            return await self.client.manifest(cid)

    async def download(
        self, manifest: Manifest, log_increment: float = 0.01
    ) -> DownloadHandle:
        """
        Downloads the dataset with the given CID from the Codex node, tracking and logging
        its progress until it is complete.

        :param manifest: the Manifest or the dataset to be downloaded.
        :param log_increment:
            how often to log progress, in terms of download completion fraction. E.g., 0.1
            will log progress every 10% of the download completed.

        :return: a :class:`DownloadHandle` object that can be used to return the current
            progress. The experiment controller will typically ask for this periodically
            to figure out if the download is complete.
        """
        handle = DownloadHandle(
            self,
            manifest=manifest,
            log_increment=log_increment,
            status_backoff=self.status_backoff,
            progress_timeout=self.progress_timeout,
        )

        handle.begin_download()

        self.ongoing_downloads[manifest.treeCid] = handle
        return handle
