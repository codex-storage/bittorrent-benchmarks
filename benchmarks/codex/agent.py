from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from benchmarks.codex.client import CodexClient
from benchmarks.core.utils import random_data

Cid = str


class CodexAgent:
    def __init__(self, client: CodexClient):
        self.client = client

    async def create_dataset(self, name: str, size: int, seed: Optional[int]) -> Cid:
        with TemporaryDirectory() as td:
            data = Path(td) / "datafile.bin"

            with data.open(mode="wb") as outfile:
                random_data(size=size, outfile=outfile, seed=seed)

            with data.open(mode="rb") as infile:
                return await self.client.upload(
                    name=name, mime_type="application/octet-stream", content=infile
                )
