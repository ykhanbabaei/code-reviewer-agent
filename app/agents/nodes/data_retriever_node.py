from github import Github, PullRequest
from langgraph.errors import NodeError
from langgraph.runtime import Runtime
from langgraph.types import Command
from langgraph.constants import END

from app.agents.context import ContextRepoInfo
from app.agents.state import PRState, PRMetadata, PRData, ChangedFile
import logging
from app.config import settings

logger = logging.getLogger(__name__)


def build_pr_data_from(pr: PullRequest) -> PRData:
    # Extract PR metadata

    pr_metadata = PRMetadata(
        title=pr.title,
        description=pr.body or "",
        author=pr.user.login,
        base_branch=pr.base.ref,
        labels=[label.name for label in pr.labels]
    )

    # Extract files changed
    files_changed = []
    for file in pr.get_files():
        files_changed.append(ChangedFile(
            filename=file.filename,
            status=file.status,
            additions=file.additions,
            deletions=file.deletions,
            patch=file.patch or "",
            full_content=file.contents_url if file.contents_url else None
        ))

    # Extract linked issues
    linked_issues = []
    if pr.body:
        # Simple extraction of #<number> from body
        import re
        linked_issues = re.findall(r'#(\d+)', pr.body)
        linked_issues = [f"#{issue}" for issue in linked_issues]

    # Aggregate PR data
    return PRData(
        pr_metadata=pr_metadata,
        files_changed=files_changed,
        linked_issues=linked_issues,
        review_comments=[]
    )

async def data_retriever_node(state: PRState, runtime: Runtime[ContextRepoInfo]):
    """Performs the connecting to remote repository and loading of the PR data."""
    logger.info(f"retrieving PR data for request {runtime.context}")
    return await data_retriever(runtime=runtime)

async def data_retriever(runtime: Runtime[ContextRepoInfo]):
    g = Github()
    repo = g.get_user(runtime.context.user_name).get_repo(runtime.context.repository)
    pr = repo.get_pull(number=runtime.context.pull_number)
    return {"pr_data": build_pr_data_from(pr)}


    # Parse it
    pr_data_dict = json.loads(json_string)
    pr_data_dict["pr_metadata"]["labels"] = []
    pr_data_dict["files_changed"] = [ChangedFile(**file) for file in pr_data_dict["files_changed"]]
    pr_data_dict["pr_metadata"] = PRMetadata(**pr_data_dict["pr_metadata"])
    return PRData(**pr_data_dict)


def data_retriever_error_handler(state: PRState, error: NodeError) -> Command:
    logger.error(f"Error in data retriever node: {error.error}")
    return Command(
        update={"error": f"Error during retrieving data: {error.error}"},
        goto=END
    )