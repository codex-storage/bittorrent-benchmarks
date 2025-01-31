from io import BytesIO

import pytest

from benchmarks.core.utils.random import random_data


@pytest.fixture
def random_file() -> BytesIO:
    b = BytesIO()
    random_data(size=2048, outfile=b)
    b.seek(0)
    return b


@pytest.mark.codex_integration
@pytest.mark.asyncio
async def test_should_upload_file(codex_client_1, random_file):
    cid = await codex_client_1.upload(
        content=random_file, name="dataset-1", mime_type="application/octet-stream"
    )

    assert cid is not None

    manifest = await codex_client_1.get_manifest(cid)

    assert manifest.cid == cid
    assert manifest.datasetSize == 2048
    assert manifest.mimetype == "application/octet-stream"
