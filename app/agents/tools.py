import requests
from collections.abc import Callable

from langchain.agents.middleware import wrap_tool_call
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.tools import tool
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

_tool_call_counts = defaultdict(int)  # keyed by thread/run id if you have one


@tool(description="""
Fetches the FULL source file. 
Call this ONLY IF ALL of the following are true:
  1. The patch contains a function call or reference you cannot find in the patch itself
  2. AND understanding that reference is required to identify a concrete bug or security issue
  3. AND the file is NOT a config, migration, test, or lock file

Do NOT call for: clean diffs, formatting changes, renames, small additions, 
missing comments, or general uncertainty. Default to NOT calling this tool.
""")
def full_file_content_provider(full_content_url: str):
    """
    retrieve full data from context source
    """
    logger.info(f"loading full source file: {full_content_url}")
    response = requests.get(full_content_url)
    data = response.json()
    raw_data_url = data["download_url"]
    response = requests.get(raw_data_url)
    source_code = response.text
    logger.info(f"Full source file loaded for url: {full_content_url}")
    return source_code


@wrap_tool_call
def handle_tool_errors(
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage]) -> ToolMessage:
    tool_name = request.tool_call["name"]
    _tool_call_counts[tool_name] += 1

    # Hard limit: block re-calls at the hook level
    if _tool_call_counts[tool_name] > 1:
        logger.debug("Tool already has been called for given url")
        return ToolMessage(
            content=(
                f"Tool '{tool_name}' has already been called. "
                "Do not call it again. Return your final review now."
            ),
            tool_call_id=request.tool_call["id"],
        )

    try:
        return handler(request)
    except Exception as e:
        logger.error(e, exc_info=True)
        return ToolMessage(
            content=(
                f"Tool error: Cannot load full content. ({e}). "
                "Do NOT retry. Review the patch only and return your final response."
            ),
            tool_call_id=request.tool_call["id"],
        )