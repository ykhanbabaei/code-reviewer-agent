from types import SimpleNamespace
import pytest

from app.agents.nodes.file_reviewer_node import build_prompt, build_error_file_review, file_reviewer_error_handler, lazily_load_agent, file_reviewer_node
from app.agents.state import ChangedFile, PRMetadata, PRState
from app.agents.context import ContextRepoInfo


class FakeNodeError:
    def __init__(self, node, error):
        self.node = node
        self.error = error


def test_build_prompt_contains_fields():
    file = ChangedFile(filename="a.py", commit_sha="abcd12345678", status="modified", additions=1, deletions=0, patch="+1")
    meta = PRMetadata(title="T", description="D", author="a", base_branch="main")
    out = build_prompt(file, meta)
    assert "Review the PR patch" in out
    assert "a.py" in out
    assert "+1" in out


def test_build_error_file_review_contains_message():
    err = FakeNodeError(node="file_reviewer_node", error=Exception("boom"))
    fr = build_error_file_review("a.py", err)
    assert hasattr(fr, 'error')
    assert "Error in file review" in fr.error


def test_file_reviewer_error_handler_updates_state():
    file = ChangedFile(filename="a.py", commit_sha="abcd12345678", status="modified", additions=1, deletions=0, patch="p")
    state = PRState(files_to_review=[file], current_file_index=0)
    err = FakeNodeError(node="file_reviewer_node", error=Exception("err"))
    cmd = file_reviewer_error_handler(state, err)
    assert cmd.update["current_file_index"] == 1
    review = cmd.update["file_reviews"][0]["review"]
    assert "Error in file review" in review["error"]


def test_lazily_load_agent_creates_agent(monkeypatch):
    # Replace create_agent with a stub
    import app.agents.nodes.file_reviewer_node as frn
    frn.agent = None
    def fake_create_agent():
        return "SENTINEL_AGENT"
    monkeypatch.setattr('app.agents.nodes.file_reviewer_node.create_agent', fake_create_agent)
    agent = lazily_load_agent()
    assert agent == "SENTINEL_AGENT"
    # subsequent call should return same object
    agent2 = lazily_load_agent()
    assert agent2 == "SENTINEL_AGENT"


@pytest.mark.asyncio
async def test_file_reviewer_node_returns_synthesizer_when_no_files():
    state = PRState(files_to_review=[], current_file_index=0)
    runtime = SimpleNamespace(context=ContextRepoInfo(token='t', user_name='u', repository='r', pull_number=1))
    res = await file_reviewer_node(state, runtime)
    assert res.goto == "synthesizer_node"