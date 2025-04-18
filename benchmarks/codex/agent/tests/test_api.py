import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient

from benchmarks.codex.agent import api
from benchmarks.codex.agent.agent import CodexAgent
from benchmarks.codex.agent.tests.fake_codex import FakeCodex
from benchmarks.codex.client.common import Manifest


@pytest.mark.asyncio
async def test_should_create_file():
    codex_client = FakeCodex()
    codex_agent = CodexAgent(codex_client)

    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.codex_agent] = lambda: codex_agent

    client = TestClient(app)

    response = client.post(
        "/api/v1/codex/dataset",
        params={"name": "dataset-1", "size": 1024, "seed": 12},
    )

    assert response.status_code == 200

    manifest = Manifest.model_validate(response.json())

    assert manifest.datasetSize == 1024


@pytest.mark.asyncio
async def test_should_report_when_download_is_complete():
    codex_client = FakeCodex()
    codex_agent = CodexAgent(codex_client)

    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.codex_agent] = lambda: codex_agent

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.post(
            "/api/v1/codex/dataset",
            params={"name": "dataset-1", "size": 1024, "seed": 12},
        )

        assert response.status_code == 200
        manifest = Manifest.model_validate(response.json())

        fake_download = codex_client.new_download(manifest)

        response = await client.post(
            "/api/v1/codex/download", json=manifest.model_dump(mode="json")
        )

        assert response.status_code == 202
        assert response.json() == {
            "status": f"http://testserver/api/v1/codex/download/{manifest.treeCid}/status"
        }

        fake_download.advance_download(blocks=1024)

        await codex_agent.ongoing_downloads[manifest.treeCid].download_task

        response = await client.get(f"api/v1/codex/download/{manifest.treeCid}/status")

        assert response.status_code == 200
        assert response.json() == {"downloaded": 1024, "total": 1024}
