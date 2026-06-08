from langgraph.runtime import Runtime

from app.agents.context import ContextRepoInfo
from app.agents.state import PRState


def chunker_node(state: PRState, runtime: Runtime[ContextRepoInfo]):
    """Chunk the PR data into smaller pieces for review."""
    # TODO chunk the PR files in case of very large file with many deletions and addition. It may not fit inside context window
    return {}


