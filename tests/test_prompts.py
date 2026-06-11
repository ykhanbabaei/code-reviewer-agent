from app.agents.prompts import FILE_REVIEWER_USER_PROMPT_TEMPLATE, FILE_REVIEWER_SYSTEM_PROMPT, FILE_REVIEWER_FEW_SHOT_EXAMPLES, RELATED_CODE_RETRIEVER_TOOL


def test_user_prompt_format():
    out = FILE_REVIEWER_USER_PROMPT_TEMPLATE.format(title="T", intent="I", file_name="f.py", file_status="modified", file_patch="+1")
    assert "Review the PR patch" in out
    assert "T" in out and "f.py" in out


def test_system_prompt_contains_tool_use():
    assert "TOOL USE" in FILE_REVIEWER_SYSTEM_PROMPT
    assert "related_code_retriever" in FILE_REVIEWER_SYSTEM_PROMPT


def test_few_shot_contains_examples():
    assert "Example 1" in FILE_REVIEWER_FEW_SHOT_EXAMPLES
    assert "Example 2" in FILE_REVIEWER_FEW_SHOT_EXAMPLES


def test_related_tool_guidance_present():
    assert "Query guidance" in RELATED_CODE_RETRIEVER_TOOL
    assert "One call per review" in RELATED_CODE_RETRIEVER_TOOL or "One call per review" in FILE_REVIEWER_SYSTEM_PROMPT


def test_constants_are_strings():
    assert isinstance(FILE_REVIEWER_USER_PROMPT_TEMPLATE, str)
    assert isinstance(FILE_REVIEWER_SYSTEM_PROMPT, str)