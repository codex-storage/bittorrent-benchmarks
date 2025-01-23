from pathlib import Path
from typing import Annotated, Optional

from fastapi import FastAPI, Depends, APIRouter, Response

from benchmarks.core.agent import AgentBuilder

from benchmarks.core.utils import megabytes
from benchmarks.deluge.agent.agent import DelugeAgent

router = APIRouter()


def deluge_agent() -> DelugeAgent:
    raise Exception("Dependency must be set")


@router.get("/api/v1/hello")
def hello():
    return {"message": "Server is up"}


@router.post("/api/v1/deluge/torrent")
def generate(
    agent: Annotated[DelugeAgent, Depends(deluge_agent)],
    name: str,
    size: int,
    seed: Optional[int],
):
    return Response(
        agent.create_torrent(name=name, size=size, seed=seed).to_string(),
        media_type="application/octet-stream",
    )


class DelugeAgentConfig(AgentBuilder):
    torrents_path: Path
    batch_size: int = megabytes(50)

    def build(self) -> FastAPI:
        app = FastAPI()
        app.include_router(router)
        agent = DelugeAgent(
            torrents_path=self.torrents_path,
            batch_size=self.batch_size,
        )
        app.dependency_overrides[deluge_agent] = lambda: agent
        return app
