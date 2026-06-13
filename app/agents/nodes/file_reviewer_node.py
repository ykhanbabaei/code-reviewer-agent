from langchain_openai import ChatOpenAI
from langgraph.errors import NodeError
from langgraph.runtime import Runtime
from langgraph.types import Command

from typing import Literal, Optional
from pydantic import BaseModel, Field

from app.agents.prompts import FILE_REVIEWER_SYSTEM_PROMPT, FILE_REVIEWER_FEW_SHOT_EXAMPLES, \
    FILE_REVIEWER_USER_PROMPT_TEMPLATE
from app.agents.context import ContextRepoInfo
from app.agents.state import PRState, PRMetadata, ChangedFile
from app.agents.tools import related_code_retriever
import logging

from app.services import cache_service
from app.services.cache_service import RedisCacheService

logger = logging.getLogger(__name__)

class CodeIssue(BaseModel):
    line_range: str = Field(
        description="e.g. '42-47' or '42' for single line"
    )
    severity: Literal["low", "medium", "high", "critical"]
    description: str = Field(description="What the issue is, in 1-2 sentences")


class FileReview(BaseModel):
    filename: str

    issues: Optional[list[CodeIssue]] = Field(
        default_factory=list,
        description=(
            "List of concrete issues found. "
            "Return an EMPTY LIST [] if the code is clean — "
            "do NOT invent minor nitpicks to populate this field."
        )
    )


    summary: Optional[str] = Field(
        default=None,
        description=(
            "1-2 sentences on what changed. If no issues found, summarize the change and explicitly state that no issues were found. "
        )
    )
    error: Optional[str] = Field(
        default=None,
        description="Populated only on exception. Leave null if review completed."
    )


def create_agent():
    model = ChatOpenAI(model="gpt-4o-mini")

    from langchain.agents import create_agent
    return create_agent(
        model=model,
        tools=[related_code_retriever],
        system_prompt=FILE_REVIEWER_SYSTEM_PROMPT,
        response_format=FileReview)


agent = None

def lazily_load_agent():
    global agent
    if agent is None:
        agent = create_agent()
    return agent

async def file_reviewer_node(state: PRState, runtime: Runtime[ContextRepoInfo]):
    current_index = (state.current_file_index or 0)
    files_count = len((state.files_to_review or []))
    if current_index >= files_count :
        return Command(
            goto="synthesizer_node"
        )

    file = state.files_to_review[(current_index or 0)]
    logger.info(f"PR file reviewing: {file.filename}")
    _agent = lazily_load_agent()
    runtime.context.retrieval_used_count = 0
    key = f"{file.commit_sha}-{file.filename}"
    redis_cache: RedisCacheService | None = (
        cache_service.get_redis_cache_service()
        if cache_service.is_redis_cache_enabled()
        else None
    )

    if redis_cache and redis_cache.exists(key):
        logger.info(f"Cached file reviewing file: {file.filename}")
        structured_response = cache_service.get_redis_cache_service().get(key)
    else:
        review = await _agent.ainvoke({"messages": [
            {"role": "user", "content": build_prompt(file, state.pr_data.pr_metadata)}
        ]})
        structured_response = review["structured_response"].model_dump()
        if redis_cache:
            redis_cache.set(key, structured_response)
    return Command(
        update={"file_reviews": [{"file": file.filename, "review": structured_response}], "current_file_index": current_index + 1},
        goto="file_reviewer_node"
    )


def build_prompt(file: ChangedFile, pr_meta: PRMetadata):
    return FILE_REVIEWER_USER_PROMPT_TEMPLATE.format(
        title=pr_meta.title,
        intent=pr_meta.description[:300],
        file_name=file.filename,
        file_status=file.status,
        file_patch=file.patch)

def file_reviewer_error_handler(state: PRState, error: NodeError) -> Command:
    logger.error(f"Node {error.node} failed with: {error.error}")
    current_index = (state.current_file_index or 0)
    file = state.files_to_review[current_index]
    return Command(
        update={"file_reviews": [{"file": file.filename, "review": build_error_file_review(file.filename, error).model_dump()}], "current_file_index": current_index + 1},
        goto="file_reviewer_node"
    )

def build_error_file_review(filename: str, error: NodeError):
    return FileReview(filename=filename, error="Error in file review: " + str(error))


