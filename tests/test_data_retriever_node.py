import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.agents.nodes import data_retriever_node as drn
from app.agents.context import ContextRepoInfo
from app.agents.state import PRState


class FakeFile:
    def __init__(self, filename, status, additions, deletions, patch, contents_url=None):
        self.filename = filename
        self.status = status
        self.additions = additions
        self.deletions = deletions
        self.patch = patch
        self.contents_url = contents_url


class FakeLabel:
    def __init__(self, name):
        self.name = name


class FakeUser:
    def __init__(self, login):
        self.login = login


class FakeBase:
    def __init__(self, ref):
        self.ref = ref


class FakePR:
    def __init__(self, title, body, user_login, base_ref, labels, files):
        self.title = title
        self.body = body
        self.user = FakeUser(user_login)
        self.base = FakeBase(base_ref)
        self.labels = [FakeLabel(l) for l in labels]
        self._files = files

    def get_files(self):
        return self._files


@pytest.mark.parametrize("body,expected_linked", [
    ("Fixes #12 and relates to #34", ["#12", "#34"]),
    (None, []),
    ("no refs here", []),
])
def test_build_pr_data_from_parses_linked_issues(body, expected_linked):
    files = [FakeFile("a.py", "modified", 1, 0, "+1", "http://c")]
    pr = FakePR(title="T", body=body, user_login="u", base_ref="main", labels=["bug"], files=files)
    pr_data = drn.build_pr_data_from(pr)
    assert pr_data.pr_metadata.title == "T"
    assert pr_data.pr_metadata.author == "u"
    assert pr_data.pr_metadata.base_branch == "main"
    assert pr_data.pr_metadata.labels == ["bug"]
    assert len(pr_data.files_changed) == 1
    assert pr_data.linked_issues == expected_linked


def test_build_pr_data_handles_file_without_contents_url():
    files = [FakeFile("b.java", "added", 5, 0, "+5", None)]
    pr = FakePR(title="T2", body="", user_login="u2", base_ref="dev", labels=[], files=files)
    pr_data = drn.build_pr_data_from(pr)
    assert pr_data.files_changed[0].full_content is None


@pytest.mark.asyncio
async def test_data_retriever_returns_pr_data_with_mocked_github(monkeypatch):
    # Fake Github client that returns our FakePR
    fake_pr = FakePR(title="X", body="#7", user_login="owner", base_ref="main", labels=["a"], files=[])

    class FakePullClient:
        def get_pull(self, number):
            return fake_pr

    class FakeRepoClient:
        def get_pull(self, number):
            return fake_pr

    class FakeUserClient:
        def get_repo(self, name):
            return FakePullClient()

    class FakeGithub:
        def get_user(self, name):
            return FakeUserClient()

    monkeypatch.setattr(drn, 'Github', FakeGithub)
    runtime = SimpleNamespace(context=ContextRepoInfo(token='t', user_name='owner', repository='repo', pull_number=1))
    res = await drn.data_retriever(runtime)
    assert 'pr_data' in res
    assert res['pr_data'].pr_metadata.title == 'X'


@pytest.mark.asyncio
async def test_data_retriever_node_delegates_to_data_retriever(monkeypatch):
    dummy = {"pr_data": "SENTINEL"}
    monkeypatch.setattr(drn, 'data_retriever', AsyncMock(return_value=dummy))
    runtime = SimpleNamespace(context=ContextRepoInfo(token='t', user_name='owner', repository='repo', pull_number=1))
    state = PRState()
    res = await drn.data_retriever_node(state, runtime)
    assert res == dummy


def test_data_retriever_error_handler_returns_end():
    fake_error = SimpleNamespace(error="boom")
    cmd = drn.data_retriever_error_handler(PRState(), fake_error)
    assert "Error during retrieving data" in cmd.update['error']
    # cmd.goto should equal END constant imported by module
    from langgraph.constants import END
    assert cmd.goto == END
