import asyncio
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from app.agents.graph import get_workflow_agent
import json

from app.services.rag_service import SourceCodeRagService, source_code_rag_service

router = APIRouter()

class PRRequest(BaseModel):
    user_name: str
    repository: str
    pull_number: Optional[int] = Field(default=0, description="pull request number, if not provided, it will default to 0 and the agent should handle it accordingly")
    token: Optional[str] = Field(default=None, description="access token for loading source code and indexing")


@router.post("/api/review/")
async def create_item(pr: PRRequest):
    async def stream():
        workflow_agent = await get_workflow_agent()
        async for item in workflow_agent.astream_pr_files({
            "user_name": pr.user_name,
            "repository": pr.repository,
            "pull_number": pr.pull_number,
            "token": pr.token,
        }):
            yield json.dumps(item) + "\n"

    return StreamingResponse(
        stream(),
        media_type="application/x-ndjson"
    )

@router.post("/api/embed/")
async def embed(pr: PRRequest):
    # Run blocking code in thread pool since SourceCodeRagService is blocking
    loop = asyncio.get_running_loop()
    _ = await loop.run_in_executor(None, lambda: source_code_rag_service.retrieve_and_embed(pr.user_name, pr.repository, pr.token))
    return "repository embedded"
