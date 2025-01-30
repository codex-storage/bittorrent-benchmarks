from typing import IO

import aiohttp
from pydantic import BaseModel
from urllib3.util import Url

API_VERSION = "v1"

Cid = str


class Manifest(BaseModel):
    cid: Cid
    treeCid: Cid
    datasetSize: int
    blockSize: int
    filename: str
    mimetype: str
    uploadedAt: int
    protected: bool


class CodexClient:
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

    async def get_manifest(self, cid: Cid) -> Manifest:
        async with aiohttp.ClientSession() as session:
            response = await session.get(
                self.codex_api_url._replace(
                    path=f"/api/codex/v1/data/{cid}/network/manifest"
                ).url,
            )

            response.raise_for_status()
            response_contents = await response.json()

        cid = response_contents.pop("cid")

        return Manifest.model_validate(dict(cid=cid, **response_contents["manifest"]))
