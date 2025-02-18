"""This module contains a REST API wrapping :class:`CodexAgent`."""

from typing import Annotated, Optional

from aiohttp import ClientResponseError
from fastapi import APIRouter, Response, Depends, HTTPException, Request, FastAPI
from fastapi.responses import JSONResponse
from pydantic_core import Url
from urllib3.util import parse_url

from benchmarks.codex.agent.agent import CodexAgent, DownloadStatus
from benchmarks.codex.client.async_client import AsyncCodexClientImpl
from benchmarks.core.agent import AgentBuilder

router = APIRouter()


def codex_agent() -> CodexAgent:
    raise Exception("Dependency must be set")


@router.get("/api/v1/hello")
async def hello():
    return {"message": "Server is up"}


@router.post("/api/v1/codex/dataset")
async def generate(
    agent: Annotated[CodexAgent, Depends(codex_agent)],
    name: str,
    size: int,
    seed: Optional[int],
):
    return Response(
        await agent.create_dataset(name=name, size=size, seed=seed),
        media_type="text/plain; charset=UTF-8",
    )


@router.post("/api/v1/codex/download")
async def download(
    request: Request, agent: Annotated[CodexAgent, Depends(codex_agent)], cid: str
):
    await agent.download(cid)
    return JSONResponse(
        status_code=202,
        content={"status": str(request.url_for("download_status", cid=cid))},
    )


@router.get("/api/v1/codex/download/{cid}/status")
async def download_status(
    agent: Annotated[CodexAgent, Depends(codex_agent)], cid: str
) -> DownloadStatus:
    if cid not in agent.ongoing_downloads:
        raise HTTPException(
            status_code=404, detail=f"There are no ongoing downloads for CID {cid}"
        )

    return agent.ongoing_downloads[cid].progress()


@router.get("/api/v1/codex/download/node-id")
async def node_id(agent: Annotated[CodexAgent, Depends(codex_agent)]):
    return agent.node_id


def client_response_error_handler(
    _: Request, exception: ClientResponseError
) -> Response:
    return JSONResponse(
        status_code=exception.status,
        content={"message": exception.message},
    )


class CodexAgentConfig(AgentBuilder):
    codex_api_url: Url
    node_id: str

    def build(self) -> FastAPI:
        app = FastAPI()
        app.include_router(router)
        # Need to disable typing (https://github.com/encode/starlette/discussions/2391)
        app.add_exception_handler(ClientResponseError, client_response_error_handler)  # type: ignore
        agent = CodexAgent(
            client=AsyncCodexClientImpl(
                codex_api_url=parse_url(str(self.codex_api_url))
            ),
            node_id=self.node_id,
        )
        app.dependency_overrides[codex_agent] = lambda: agent
        return app
