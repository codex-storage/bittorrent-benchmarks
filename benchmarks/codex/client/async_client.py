"""Async Client implementation for the base Codex API."""

from abc import ABC, abstractmethod

from contextlib import asynccontextmanager
from typing import IO, AsyncIterator, AsyncGenerator

import aiohttp
from urllib3.util import Url

from benchmarks.codex.client.common import Manifest, Cid
from benchmarks.core.utils.streams import BaseStreamReader


class AsyncCodexClient(ABC):
    @abstractmethod
    async def upload(self, name: str, mime_type: str, content: IO) -> Cid:
        pass

    @abstractmethod
    async def manifest(self, cid: Cid) -> Manifest:
        pass

    @asynccontextmanager
    @abstractmethod
    def download(self, cid: Cid) -> AsyncGenerator[BaseStreamReader, None]:
        pass


class AsyncCodexClientImpl(AsyncCodexClient):
    """A lightweight async wrapper built around the Codex REST API."""

    def __init__(self, codex_api_url: Url):
        self.codex_api_url = codex_api_url

    async def upload(self, name: str, mime_type: str, content: IO) -> Cid:
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                self.codex_api_url._replace(path="/api/codex/v1/data").url,
                headers={
                    aiohttp.hdrs.CONTENT_TYPE: mime_type,
                    aiohttp.hdrs.CONTENT_DISPOSITION: f'attachment; filename="{name}"',
                },
                data=content,
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

    @asynccontextmanager
    async def download(self, cid: Cid) -> AsyncIterator[BaseStreamReader]:
        async with aiohttp.ClientSession() as session:
            response = await session.get(
                self.codex_api_url._replace(path=f"/api/codex/v1/data/{cid}").url,
            )

            response.raise_for_status()

            yield response.content
