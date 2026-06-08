from langgraph.runtime import Runtime

from app.agents.context import ContextRepoInfo
from app.agents.state import PRState
import logging

logger = logging.getLogger(__name__)


def synthesizer_node(state: PRState, runtime: Runtime[ContextRepoInfo]):
    logger.info(f"summarising result for PR request: {runtime.context}")
    all_issues = [
        issue.model_dump()
        for review in (state.file_reviews or []) # typed FileReview objects
        for issue in review.get("issues", [])
    ]
    # agent call to summarize
    return {
        "summary": "agent call is required",
        "overall_severity": "agent call is required",
        "all_issues": all_issues
    }
