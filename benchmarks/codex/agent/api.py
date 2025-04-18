"""This module contains a REST API wrapping :class:`CodexAgent`."""

import logging
from typing import Annotated, Optional

from aiohttp import ClientResponseError
from fastapi import APIRouter, Response, Depends, HTTPException, Request, FastAPI
from fastapi.responses import JSONResponse
from pydantic_core import Url
from urllib3.util import parse_url

from benchmarks.codex.agent.agent import CodexAgent, DownloadStatus
from benchmarks.codex.client.async_client import AsyncCodexClientImpl
from benchmarks.codex.client.common import Manifest
from benchmarks.core.agent import AgentBuilder

router = APIRouter()

logger = logging.getLogger(__name__)


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
) -> Manifest:
    return await agent.create_dataset(name=name, size=size, seed=seed)


@router.post("/api/v1/codex/download")
async def download(
    request: Request,
    agent: Annotated[CodexAgent, Depends(codex_agent)],
    manifest: Manifest,
):
    await agent.download(manifest)
    return JSONResponse(
        status_code=202,
        content={
            "status": str(request.url_for("download_status", cid=manifest.treeCid))
        },
    )


@router.get("/api/v1/codex/download/{cid}/status")
async def download_status(
    agent: Annotated[CodexAgent, Depends(codex_agent)], cid: str
) -> DownloadStatus:
    download = agent.ongoing_downloads.get(cid)
    if download is None:
        raise HTTPException(
            status_code=404, detail=f"There are no ongoing downloads for CID {cid}"
        )

    assert download.download_task is not None

    if download.download_task.done():
        exception = download.download_task.exception()
        if exception is not None:
            logger.error("Error during download:", exc_info=exception)
            raise HTTPException(
                status_code=500, detail=f"Error during download: {exception}"
            )

    return download.progress()


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
