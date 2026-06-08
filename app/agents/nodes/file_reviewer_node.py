from time import sleep

from langchain_openai import ChatOpenAI
from langgraph.errors import NodeError
from langgraph.runtime import Runtime
from langgraph.types import Command

from typing import Literal, Optional
from pydantic import BaseModel, Field
from app.config import settings
from app.agents.context import ContextRepoInfo
from app.agents.state import PRState, PRMetadata, ChangedFile
from app.agents.tools import full_file_content_provider, handle_tool_errors
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a senior code reviewer. Follow these rules strictly:

ISSUES LIST:
- Only add an entry if there is a real, concrete problem in the code
- Minor style preferences are NOT issues unless the project has a linter rule for it
- If the code looks correct and clean, return issues: []
- Do NOT add issues like "consider adding comments" or "could be more readable"

SEVERITY:
- "clean"    → zero issues found
- "low"      → cosmetic or very minor, non-blocking
- "medium"   → should fix before merge, but not a blocker
- "high"     → likely bug or security concern, blocks merge
- "critical" → data loss, auth bypass, crash — must fix

has_breaking_change:
- Default is false
- Only set true if you can point to a specific caller that would break

needs_tests:
- Default is false  
- Only set true if new branching logic was added (if/else, try/catch, new function)
- Refactors and renames do NOT need new tests

When in doubt, lean toward: empty issues list, severity=clean, booleans=false.

TOOL USE — full_file_content_provider:
You have access to a tool that fetches the full source file.
Call it ONLY when ALL of these conditions are met:
  - The patch references a symbol (function, class, variable) defined outside the patch
  - AND that symbol is directly relevant to a suspected bug or security issue
  - AND the file type is NOT: test, migration, config, lockfile, or generated code

NEVER call the tool for:
  - Patches under 50 lines that are self-contained
  - Formatting, renaming, or comment-only changes  
  - Files ending in: .json, .lock, .yaml, .yml, .md, .txt, .env
  - When you are only "curious" about surrounding context
  - When the patch is readable and no concrete issue is suspected

Default behavior: review the patch directly. Tool use is the exception, not the rule.

"""

FEW_SHOT_EXAMPLES = """
   ## Example 1 — Clean file, no issues

   Diff:
   - return user.name
   + return user.display_name or user.name

   Expected output:
   {
     "filename": "src/user.py",
     "issues": [],
     "severity": "clean",
     "summary": "No issues found. Adds fallback to display_name with backward compatibility.",
     "has_breaking_change": false,
     "needs_tests": false
   }

   ## Example 2 — Real issue found

   Diff:
   + password = request.get("password")
   + db.execute(f"SELECT * FROM users WHERE password = '{password}'")

   Expected output:
   {
     "filename": "src/auth.py",
     "issues": [
       {
         "line_range": "42-43",
         "category": "security",
         "severity": "critical",
         "description": "Raw string interpolation into SQL query allows injection attacks.",
         "suggestion": "Use parameterised queries: db.execute('SELECT * FROM users WHERE password = ?', (password,))"
       }
     ],
     "severity": "critical",
     "summary": "Critical SQL injection vulnerability found in password lookup.",
     "has_breaking_change": false,
     "needs_tests": true
   }
   
   ## Example 3 — Patch is sufficient, tool NOT called
    Diff:
    - timeout = 30
    + timeout = 60
    Full Content Url: https://api.github.com/repos/.../contents/config.py
    
    Reasoning: The change is self-contained. The value being changed is visible 
    in the patch. No external symbol needs to be resolved. Tool not called.
    
    Expected output:
    {
      "filename": "config.py",
      "issues": [],
      "severity": "clean",
      "summary": "Timeout doubled. No issues found.",
      "has_breaking_change": false,
      "needs_tests": false
    }
    
    ## Example 4 — Tool IS justified
    Diff:
    + result = process_payment(user, amount)
    Full Content Url: https://api.github.com/repos/.../contents/billing.py
    
    Reasoning: process_payment is called but not defined in the patch. 
    A payment function could have error handling or validation issues 
    that are hidden in its definition. Tool called once.
    
    (tool returns full file content)
    Expected output:
    {
      "filename": "billing.py",
      "issues": [...],
      ...
    }

   """

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
        tools=[full_file_content_provider],
        middleware=[handle_tool_errors],
        system_prompt=SYSTEM_PROMPT,
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
            {"role": "user", "content": build_prompt(file, state.pr_data.pr_metadata)},
            {"role": "user", "content": FEW_SHOT_EXAMPLES}
        ]})
    return Command(
        update={"file_reviews": [{"file": file.filename, "review": review["structured_response"].model_dump()}], "current_file_index": current_index + 1},
        goto="file_reviewer_node"
    )


def build_prompt(file: ChangedFile, pr_meta: PRMetadata):
    return f"""
    Review the PR patch below and return a structured response.

    PR: {pr_meta.title}
    Intent: {pr_meta.description[:300]}
    File: {file.filename} ({file.status})
    Patch: {file.patch}
    
    TOOL USE DECISION (follow strictly):
    - If the patch is self-contained and all changed code is visible → review directly, do NOT call the tool
    - If the patch calls or references a symbol NOT visible in the patch AND that symbol is critical to identifying a real bug → call the tool ONCE using: {file.full_content}
    - Lock files, configs, migrations, generated files → NEVER call the tool
    
    When in doubt → do NOT call the tool. Patch-only review is preferred.
    """


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


