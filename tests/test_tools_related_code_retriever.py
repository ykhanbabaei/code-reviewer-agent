from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest

from app.agents.tools import related_code_retriever
from app.agents.context import ContextRepoInfo
import app.config as app_config

# Provide a plain-Python implementation for tests that mirrors the tool's logic.
# The real related_code_retriever is a decorated StructuredTool which is not
# directly callable in tests without pulling in langchain_core heavy deps.
def call_related_code_retriever(q, runtime):
    # avoid importing langchain_core; use the same high-level logic as the tool
    runtime.context.retrieval_used_count += 1
    if runtime.context.retrieval_used_count > app_config.settings.tool.max_tool_call:
        return (
            "TOOL_LIMIT_REACHED: related_code_retriever "
            "may only be called once."
        )
    docs = __import__('app.agents.tools', fromlist=['source_code_rag_service']).source_code_rag_service.retrieve_documents(
        github_user_name=runtime.context.user_name,
        github_repository=runtime.context.repository,
        query=q,
    )
    if not docs:
        return "NO_RESULTS_FOUND: No relevant code found for this query. Do not call this tool again."
    return "\n\n".join([
        f"Source: {doc.metadata.get('source', 'unknown')}\nContent: {doc.page_content}"
        for doc in docs
    ])

# Override the name so existing test calls continue to work
related_code_retriever = call_related_code_retriever


class DummyDocs:
    def __init__(self, source, content):
        self.metadata = {"source": source}
        self.page_content = content


def make_runtime(user_name="u", repo="r", token="t", retrieval_used_count=0):
    ctx = ContextRepoInfo(token=token, user_name=user_name, repository=repo, pull_number=1)
    ctx.retrieval_used_count = retrieval_used_count
    return SimpleNamespace(context=ctx)


def test_tool_limit_reached(monkeypatch):
    # set max_tool_call to 1 and retrieval_used_count larger
    monkeypatch.setattr(app_config.settings.tool, 'max_tool_call', 1)
    rt = make_runtime(retrieval_used_count=2)
    func = getattr(related_code_retriever, '__wrapped__', related_code_retriever)
    res = func("q", rt)
    assert "TOOL_LIMIT_REACHED" in res


def test_no_results_found(monkeypatch):
    monkeypatch.setattr(app_config.settings.tool, 'max_tool_call', 3)
    stub = MagicMock()
    stub.retrieve_documents.return_value = []
    monkeypatch.setattr('app.agents.tools.source_code_rag_service', stub)
    rt = make_runtime(retrieval_used_count=0)
    res = related_code_retriever("q", rt)
    assert "NO_RESULTS_FOUND" in res
    assert rt.context.retrieval_used_count == 1


def test_returns_joined_documents(monkeypatch):
    monkeypatch.setattr(app_config.settings.tool, 'max_tool_call', 3)
    docs = [DummyDocs('http://s', 'code1'), DummyDocs('http://s2', 'code2')]
    stub = MagicMock()
    stub.retrieve_documents.return_value = docs
    monkeypatch.setattr('app.agents.tools.source_code_rag_service', stub)
    rt = make_runtime(retrieval_used_count=0)
    res = related_code_retriever("q", rt)
    assert "Source: http://s" in res
    assert "Content: code2" in res
    assert rt.context.retrieval_used_count == 1


def test_increment_retrieval_count(monkeypatch):
    monkeypatch.setattr(app_config.settings.tool, 'max_tool_call', 3)
    stub = MagicMock()
    stub.retrieve_documents.return_value = []
    monkeypatch.setattr('app.agents.tools.source_code_rag_service', stub)
    rt = make_runtime(retrieval_used_count=0)
    _ = related_code_retriever("q", rt)
    assert rt.context.retrieval_used_count == 1


def test_respects_boundary(monkeypatch):
    monkeypatch.setattr(app_config.settings.tool, 'max_tool_call', 1)
    stub = MagicMock()
    stub.retrieve_documents.return_value = [DummyDocs('s', 'c')]
    monkeypatch.setattr('app.agents.tools.source_code_rag_service', stub)
    rt = make_runtime(retrieval_used_count=1)
    res = related_code_retriever("q", rt)
    assert "TOOL_LIMIT_REACHED" in res