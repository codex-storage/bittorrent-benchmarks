from typing import Annotated, Optional

from fastapi import APIRouter, Response, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from benchmarks.codex.agent.agent import CodexAgent, DownloadStatus

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
