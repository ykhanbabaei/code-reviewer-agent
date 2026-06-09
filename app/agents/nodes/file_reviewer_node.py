from time import sleep

from langchain_openai import ChatOpenAI
from langgraph.errors import NodeError
from langgraph.runtime import Runtime
from langgraph.types import Command

from typing import Literal, Optional
from pydantic import BaseModel, Field

from app.agents.prompts import FILE_REVIEWER_SYSTEM_PROMPT, FILE_REVIEWER_FEW_SHOT_EXAMPLES, \
    FILE_REVIEWER_USER_PROMPT_TEMPLATE
from app.config import settings
from app.agents.context import ContextRepoInfo
from app.agents.state import PRState, PRMetadata, ChangedFile
from app.agents.tools import related_code_retriever
import logging

logger = logging.getLogger(__name__)

class CodeIssue(BaseModel):
    line_range: str = Field(
        description="e.g. '42-47' or '42' for single line"
    )
    category: Literal[
        "bug", "security", "performance",
        "style", "test_coverage", "logic_error"
    ]
    severity: Literal["low", "medium", "high", "critical"]
    description: str = Field(description="What the issue is, in 1-2 sentences")
    suggestion: str = Field(description="How to fix it, concretely")


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

    severity: Optional[Literal["clean", "low", "medium", "high", "critical"]] = Field(
        default=None,
        description=(
            "Overall severity of this file. "
            "Use 'clean' if there are zero issues. "
            "Only escalate if there is a real, concrete problem."
        )
    )

    summary: Optional[str] = Field(
        default=None,
        description=(
            "1-2 sentences describing what changed in this file. "
            "If no issues found, say so explicitly e.g. "
            "'No issues found. This change adds X.'"
        )
    )

    error: Optional[str] = Field(
        default=None,
        description=(
            "Error field in case of exceptions during review. "
            "If this is populated, other fields may be unreliable. "
            "Leave empty if review completed without exceptions."
        )
    )

    has_breaking_change: Optional[bool] = Field(
        default=None,
        description=(
            "True ONLY if this change breaks an existing public API, "
            "removes a required field, or changes behaviour callers depend on. "
            "Default to False when uncertain."
        )
    )

    needs_tests: Optional[bool] = Field(
        default=None,
        description=(
            "True ONLY if new logic was added that has no corresponding test. "
            "False for refactors, renames, config changes, or already-tested paths."
        )
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
    if settings.IS_MOCK:
        review = MOCK_INVOKE()
    else:
        _agent = lazily_load_agent()
        review = await _agent.ainvoke({"messages": [
            {"role": "user", "content": FILE_REVIEWER_FEW_SHOT_EXAMPLES},
            {"role": "user", "content": build_prompt(file, state.pr_data.pr_metadata)}
        ]})
    return Command(
        update={"file_reviews": [{"file": file.filename, "review": review["structured_response"].model_dump()}], "current_file_index": current_index + 1},
        goto="file_reviewer_node"
    )


def build_prompt(file: ChangedFile, pr_meta: PRMetadata):
    return FILE_REVIEWER_USER_PROMPT_TEMPLATE.format(
        title=pr_meta.title,
        intent=pr_meta.description[:300],
        file_name=file.filename,
        file_status=file.status,
        file_patch=file.patch)


def MOCK_INVOKE():
    sleep(2)
    return {
        "structured_response": FileReview(
       filename="src/user.py",
       issues=[],
       severity="clean",
       summary="No issues found. Adds fallback to display_name with backward compatibility.",
       has_breaking_change=False,
       needs_tests=False)
    }


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


