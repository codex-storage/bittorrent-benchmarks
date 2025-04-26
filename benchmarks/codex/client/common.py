import math

from pydantic import BaseModel

API_VERSION = "v1"

Cid = str


class Manifest(BaseModel):
    cid: Cid
    treeCid: Cid
    datasetSize: int
    blockSize: int
    filename: str
    mimetype: str
    protected: bool

    @property
    def block_count(self) -> int:
        return math.ceil(self.datasetSize / self.blockSize)

    @staticmethod
    def from_codex_api_response(response: dict) -> "Manifest":
        return Manifest.model_validate(
            dict(cid=response["cid"], **response["manifest"])
        )
