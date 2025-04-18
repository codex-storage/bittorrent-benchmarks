"""Async Client implementation for the base Codex API."""

from abc import ABC, abstractmethod
from typing import IO, Optional

import aiohttp
from aiohttp import ClientTimeout
from pydantic import BaseModel
from urllib3.util import Url

from benchmarks.codex.client.common import Manifest, Cid


class DownloadStatus(BaseModel):
    downloaded: int
    total: int

    def as_percent(self) -> float:
        return (self.downloaded * 100) / self.total

    def is_complete(self) -> bool:
        return self.downloaded == self.total


class AsyncCodexClient(ABC):
    @abstractmethod
    async def upload(
        self,
        name: str,
        mime_type: str,
        content: IO,
        timeout: Optional[ClientTimeout] = None,
    ) -> Cid:
        pass

    @abstractmethod
    async def manifest(self, cid: Cid) -> Manifest:
        pass

    @abstractmethod
    async def download(
        self, manifest: Manifest, timeout: Optional[ClientTimeout] = None
    ) -> Cid:
        pass

    @abstractmethod
    async def download_status(self, dataset: Cid) -> DownloadStatus:
        pass


class AsyncCodexClientImpl(AsyncCodexClient):
    """A lightweight async wrapper built around the Codex REST API."""

    def __init__(self, codex_api_url: Url):
        self.codex_api_url = codex_api_url

    async def upload(
        self,
        name: str,
        mime_type: str,
        content: IO,
        timeout: Optional[ClientTimeout] = None,
    ) -> Cid:
        async with aiohttp.ClientSession(timeout=ClientTimeout()) as session:
            response = await session.post(
                self.codex_api_url._replace(path="/api/codex/v1/data").url,
                headers={
                    aiohttp.hdrs.CONTENT_TYPE: mime_type,
                    aiohttp.hdrs.CONTENT_DISPOSITION: f'attachment; filename="{name}"',
                },
                data=content,
                timeout=timeout,
            )

            response.raise_for_status()

            return await response.text()

    async def manifest(self, cid: Cid) -> Manifest:
        async with aiohttp.ClientSession() as session:
            response = await session.get(
                self.codex_api_url._replace(
                    path=f"/api/codex/v1/data/{cid}/network/manifest"
                ).url,
            )

            response.raise_for_status()
            response_contents = await response.json()

        return Manifest.from_codex_api_response(response_contents)

    async def download(
        self, manifest: Manifest, timeout: Optional[ClientTimeout] = None
    ) -> Cid:
        async with aiohttp.ClientSession(timeout=ClientTimeout()) as session:
            response = await session.post(
                self.codex_api_url._replace(path="/api/codex/v1/download").url,
                json={
                    "cid": manifest.cid,
                    "manifest": manifest.model_dump(exclude={"cid"}, mode="json"),
                },
            )

            response.raise_for_status()
            response_contents = await response.json()

            return response_contents["downloadId"]

    async def download_status(self, dataset: Cid) -> DownloadStatus:
        async with aiohttp.ClientSession() as session:
            response = await session.get(
                self.codex_api_url._replace(
                    path=f"/api/codex/v1/download/{dataset}"
                ).url,
            )

            response.raise_for_status()
            response_contents = await response.json()

        return DownloadStatus(
            downloaded=response_contents["downloaded"], total=response_contents["total"]
        )

    async def leave_swarm(self, dataset: Cid) -> None:
        async with aiohttp.ClientSession() as session:
            response = await session.delete(
                self.codex_api_url._replace(
                    path=f"/api/codex/v1/download/{dataset}"
                ).url,
            )

            response.raise_for_status()
