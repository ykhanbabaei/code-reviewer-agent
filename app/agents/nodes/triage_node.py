from langgraph.runtime import Runtime

from app.agents.context import ContextRepoInfo
from app.agents.state import PRState
import logging

logger = logging.getLogger(__name__)


def triage_node(state: PRState, runtime: Runtime[ContextRepoInfo]):
    """Decide which files need deep review vs. can be skipped."""
    important = [
        f for f in state.pr_data.files_changed
        if not f.filename.endswith((".lock", ".md", ".json"))
        and f.additions + f.deletions > 2
    ]
    logger.info(f"code reviewing {len(important)} PR files for request: {runtime.context}")
    return {"files_to_review": important, "current_file_index": 0}