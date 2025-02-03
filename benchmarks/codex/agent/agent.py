import asyncio
import logging
from asyncio import Task
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, Dict

from pydantic import BaseModel

from benchmarks.codex.agent.codex_client import CodexClient, Manifest
from benchmarks.codex.logging import CodexDownloadMetric
from benchmarks.core.utils.random import random_data
from benchmarks.core.utils.streams import BaseStreamReader

Cid = str

EMPTY_STREAM_BACKOFF = 0.1

logger = logging.getLogger(__name__)


class DownloadStatus(BaseModel):
    downloaded: int
    total: int


class DownloadHandle:
    def __init__(
        self,
        parent: "CodexAgent",
        manifest: Manifest,
        download_stream: BaseStreamReader,
        read_increment: float = 0.01,
    ):
        self.parent = parent
        self.manifest = manifest
        self.bytes_downloaded = 0
        self.read_increment = read_increment
        self.download_stream = download_stream
        self.download_task: Optional[Task[None]] = None

    def begin_download(self) -> Task:
        self.download_task = asyncio.create_task(self._download_loop())
        return self.download_task

    async def _download_loop(self):
        step_size = int(self.manifest.datasetSize * self.read_increment)

        while not self.download_stream.at_eof():
            step = min(step_size, self.manifest.datasetSize - self.bytes_downloaded)
            bytes_read = await self.download_stream.read(step)
            # We actually have no guarantees that an empty read means EOF, so we just back off
            # a bit.
            if not bytes_read:
                await asyncio.sleep(EMPTY_STREAM_BACKOFF)
            self.bytes_downloaded += len(bytes_read)

            logger.info(
                CodexDownloadMetric(
                    cid=self.manifest.cid,
                    value=self.bytes_downloaded,
                    node=self.parent.node_id,
                )
            )

        if self.bytes_downloaded < self.manifest.datasetSize:
            raise EOFError(
                f"Got EOF too early: download size ({self.bytes_downloaded}) was less "
                f"than expected ({self.manifest.datasetSize})."
            )

        if self.bytes_downloaded > self.manifest.datasetSize:
            raise ValueError(
                f"Download size ({self.bytes_downloaded}) was greater than expected "
                f"({self.manifest.datasetSize})."
            )

    def progress(self) -> DownloadStatus:
        if self.download_task is None:
            return DownloadStatus(downloaded=0, total=self.manifest.datasetSize)

        if self.download_task.done():
            # This will bubble exceptions up, if any.
            self.download_task.result()

        return DownloadStatus(
            downloaded=self.bytes_downloaded, total=self.manifest.datasetSize
        )


class CodexAgent:
    def __init__(self, client: CodexClient, node_id: str = "unknown") -> None:
        self.client = client
        self.node_id = node_id
        self.ongoing_downloads: Dict[Cid, DownloadHandle] = {}

    async def create_dataset(self, name: str, size: int, seed: Optional[int]) -> Cid:
        with TemporaryDirectory() as td:
            data = Path(td) / "datafile.bin"

            with data.open(mode="wb") as outfile:
                random_data(size=size, outfile=outfile, seed=seed)

            with data.open(mode="rb") as infile:
                return await self.client.upload(
                    name=name, mime_type="application/octet-stream", content=infile
                )

    async def download(self, cid: Cid, read_increment: float = 0.01) -> DownloadHandle:
        if cid in self.ongoing_downloads:
            return self.ongoing_downloads[cid]

        handle = DownloadHandle(
            self,
            manifest=await self.client.get_manifest(cid),
            download_stream=await self.client.download(cid),
            read_increment=read_increment,
        )

        handle.begin_download()

        self.ongoing_downloads[cid] = handle
        return handle
