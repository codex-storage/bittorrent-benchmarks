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
    uploadedAt: int
    protected: bool
