from typing import Dict, Optional, IO

from aiohttp import ClientTimeout

from benchmarks.codex.client.async_client import AsyncCodexClient, Cid, DownloadStatus
from benchmarks.codex.client.common import Manifest


class FakeDownload:
    def __init__(self, manifest: Manifest) -> None:
        self.manifest = manifest
        self.downloaded = 0
        self.exception: Optional[Exception] = None

    def advance_download(self, blocks: int):
        self.downloaded += blocks
        print("Advance download to", self.downloaded)
        assert (
            self.downloaded <= self.manifest.block_count
        ), "Downloaded blocks exceed total blocks"

    def abort(self, exception: Exception):
        self.exception = exception


class FakeCodex(AsyncCodexClient):
    def __init__(self) -> None:
        self.manifests: Dict[Cid, Manifest] = {}
        self.ongoing_downloads: Dict[Cid, FakeDownload] = {}

    async def upload(
        self,
        name: str,
        mime_type: str,
        content: IO,
        timeout: Optional[ClientTimeout] = None,
    ) -> Cid:
        data = content.read()
        cid = "Qm" + str(hash(data))
        self.manifests[cid] = Manifest(
            cid=cid,
            treeCid=f"{cid}treeCid",
            datasetSize=len(data),
            mimetype=mime_type,
            blockSize=1,
            filename=name,
            protected=False,
        )
        return cid

    async def manifest(self, cid: Cid) -> Manifest:
        return self.manifests[cid]

    async def download(
        self, manifest: Manifest, timeout: Optional[ClientTimeout] = None
    ) -> Cid:
        if manifest.treeCid not in self.ongoing_downloads:
            raise ValueError("You need to create a " "download before initiating it")
        return manifest.treeCid

    def new_download(self, manifest: Manifest) -> FakeDownload:
        """Creates a download which we can then use to simulate progress."""
        handle = FakeDownload(manifest)
        self.ongoing_downloads[manifest.treeCid] = handle
        return handle

    async def download_status(self, dataset: Cid) -> DownloadStatus:
        download = self.ongoing_downloads[dataset]
        if download.exception:
            raise download.exception
        return DownloadStatus(
            downloaded=download.downloaded,
            total=download.manifest.block_count,
        )
