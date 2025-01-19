from fastapi import FastAPI
from starlette.testclient import TestClient
from torrentool.torrent import Torrent

from benchmarks.deluge.agent import api
from benchmarks.deluge.agent.agent import DelugeAgent
from benchmarks.deluge.agent.api import deluge_agent


def test_should_return_a_valid_byte_encoded_torrent_object(tmp_path):
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[deluge_agent] = lambda: DelugeAgent(tmp_path)

    client = TestClient(app)
    response = client.post(
        "/api/v1/deluge/torrent",
        params={"name": "dataset-1", "size": 1024, "seed": 12},
    )

    assert response.status_code == 200
    torrent = Torrent.from_string(response.content)

    assert torrent.name == "dataset-1"
    assert torrent.total_size == 1024
