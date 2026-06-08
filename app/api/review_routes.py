from fastapi import APIRouter
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from app.agents.graph import workflow_agent
import json

router = APIRouter()

class PRRequest(BaseModel):
    user_name: str
    repository: str
    pull_number: int


@router.post("/review/")
async def create_item(pr: PRRequest):
    async def stream():
        async for item in workflow_agent.astream_pr_files({
            "user_name": pr.user_name,
            "repository": pr.repository,
            "pull_number": pr.pull_number,
        }):
            yield json.dumps(item) + "\n"

    return StreamingResponse(
        stream(),
        media_type="application/x-ndjson"
    )
