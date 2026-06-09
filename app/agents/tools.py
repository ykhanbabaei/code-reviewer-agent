from langchain_core.tools import tool
import logging

from langgraph.prebuilt import ToolRuntime

from app.agents.context import ContextRepoInfo
from app.agents.prompts import RELATED_CODE_RETRIEVER_TOOL
from app.services.rag_service import source_code_rag_service

logger = logging.getLogger(__name__)


@tool(description=RELATED_CODE_RETRIEVER_TOOL)
def related_code_retriever(q: str, runtime: ToolRuntime[ContextRepoInfo]):
    logger.info(f"loading related code file called for repository: {runtime.context.repository}")
    docs = source_code_rag_service.retrieve_documents(
        github_user_name=runtime.context.user_name,
        github_repository=runtime.context.repository,
        query=q
    )
    logger.info(f"data retrieval tool called and loaded {len(docs)} documents")
    if not docs:
        return "NO_RESULTS_FOUND: No relevant code found for this query. Do not call this tool again."
    return "\n\n".join([
        f"Source: {doc.metadata.get('source', 'unknown')}\nContent: {doc.page_content}"
        for doc in docs
    ])
