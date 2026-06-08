"""Unit tests for data_retriever_node module."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from langgraph.runtime import Runtime
import json

from app.agents.state import PRState, PRMetadata, ChangedFile, PRData
from app.agents.context import ContextRepoInfo
from app.agents.nodes.data_retriever_node import (
    build_pr_data_from,
    mock_build_pr_data_from,
    data_retriever_node,
    data_retriever
)


class TestBuildPrDataFrom:
    """Tests for build_pr_data_from function."""

    def create_mock_pr(self):
        """Create a mock GitHub PR object."""
        mock_pr = Mock()
        mock_pr.title = "Add new feature"
        mock_pr.body = "Closes #123\nCloses #456"
        mock_pr.user.login = "octocat"
        mock_pr.base.ref = "main"

        # Mock labels
        mock_label_1 = Mock()
        mock_label_1.name = "enhancement"
        mock_label_2 = Mock()
        mock_label_2.name = "bug"
        mock_pr.labels = [mock_label_1, mock_label_2]

        # Mock files
        mock_file_1 = Mock()
        mock_file_1.filename = "src/main.py"
        mock_file_1.status = "modified"
        mock_file_1.additions = 20
        mock_file_1.deletions = 5
        mock_file_1.patch = "@@ -1,5 +1,8 @@ ..."
        mock_file_1.contents_url = "https://api.github.com/repos/user/repo/contents/src/main.py"

        mock_file_2 = Mock()
        mock_file_2.filename = "README.md"
        mock_file_2.status = "added"
        mock_file_2.additions = 10
        mock_file_2.deletions = 0
        mock_file_2.patch = "@@ -0,0 +1,10 @@ ..."
        mock_file_2.contents_url = "https://api.github.com/repos/user/repo/contents/README.md"

        mock_pr.get_files.return_value = [mock_file_1, mock_file_2]

        return mock_pr

    def test_build_pr_data_extracts_metadata(self):
        """Test that PR metadata is correctly extracted."""
        mock_pr = self.create_mock_pr()

        pr_data = build_pr_data_from(mock_pr)

        assert pr_data.pr_metadata.title == "Add new feature"
        assert pr_data.pr_metadata.description == "Closes #123\nCloses #456"
        assert pr_data.pr_metadata.author == "octocat"
        assert pr_data.pr_metadata.base_branch == "main"
        assert pr_data.pr_metadata.labels == ["enhancement", "bug"]

    def test_build_pr_data_extracts_files_changed(self):
        """Test that files_changed list is populated."""
        mock_pr = self.create_mock_pr()

        pr_data = build_pr_data_from(mock_pr)

        assert len(pr_data.files_changed) == 2
        assert pr_data.files_changed[0].filename == "src/main.py"
        assert pr_data.files_changed[0].status == "modified"
        assert pr_data.files_changed[0].additions == 20
        assert pr_data.files_changed[0].deletions == 5
        assert pr_data.files_changed[1].filename == "README.md"

    def test_build_pr_data_extracts_linked_issues(self):
        """Test that linked issues are extracted from PR body."""
        mock_pr = self.create_mock_pr()

        pr_data = build_pr_data_from(mock_pr)

        assert "#123" in pr_data.linked_issues
        assert "#456" in pr_data.linked_issues

    def test_build_pr_data_empty_body(self):
        """Test handling of PR with no body."""
        mock_pr = self.create_mock_pr()
        mock_pr.body = None

        pr_data = build_pr_data_from(mock_pr)

        assert pr_data.pr_metadata.description == ""
        assert pr_data.linked_issues == []

    def test_build_pr_data_no_linked_issues(self):
        """Test PR with no linked issues."""
        mock_pr = self.create_mock_pr()
        mock_pr.body = "This is a regular PR with no issue references"

        pr_data = build_pr_data_from(mock_pr)

        assert pr_data.linked_issues == []

    def test_build_pr_data_preserves_patch_content(self):
        """Test that patch content is preserved exactly."""
        mock_pr = self.create_mock_pr()
        patch_content = "@@ -1,3 +1,5 @@ def foo():\n+    pass"
        mock_pr.get_files.return_value[0].patch = patch_content

        pr_data = build_pr_data_from(mock_pr)

        assert pr_data.files_changed[0].patch == patch_content

    def test_build_pr_data_handles_missing_contents_url(self):
        """Test handling of files without contents_url."""
        mock_pr = self.create_mock_pr()
        mock_pr.get_files.return_value[0].contents_url = None

        pr_data = build_pr_data_from(mock_pr)

        assert pr_data.files_changed[0].full_content is None

    def test_build_pr_data_handles_empty_patch(self):
        """Test handling of files with empty patch."""
        mock_pr = self.create_mock_pr()
        mock_pr.get_files.return_value[0].patch = None

        pr_data = build_pr_data_from(mock_pr)

        assert pr_data.files_changed[0].patch == ""

    def test_build_pr_data_file_statuses(self):
        """Test that different file statuses are preserved."""
        mock_pr = self.create_mock_pr()
        statuses = ["modified", "added", "deleted", "renamed"]

        for i, status in enumerate(statuses):
            mock_file = Mock()
            mock_file.filename = f"file{i}"
            mock_file.status = status
            mock_file.additions = 10 * (i + 1)
            mock_file.deletions = 5 * (i + 1)
            mock_file.patch = f"@@ patch{i} @@"
            mock_file.contents_url = f"https://api.github.com/repos/user/repo/contents/file{i}"
            mock_pr.get_files.return_value = [mock_file]

            pr_data = build_pr_data_from(mock_pr)
            assert pr_data.files_changed[0].status == status


class TestMockBuildPrDataFrom:
    """Tests for mock_build_pr_data_from function."""

    def test_mock_pr_data_structure(self):
        """Test that mock PR data has correct structure."""
        pr_data = mock_build_pr_data_from()

        assert pr_data.pr_metadata.title == "Feature/unregister"
        assert pr_data.pr_metadata.author == "ykhanbabaei"
        assert pr_data.pr_metadata.base_branch == "main"
        assert len(pr_data.files_changed) == 3

    def test_mock_pr_data_file_count(self):
        """Test that mock PR has expected number of files."""
        pr_data = mock_build_pr_data_from()

        assert len(pr_data.files_changed) == 3

    def test_mock_pr_data_file_details(self):
        """Test specific file details in mock data."""
        pr_data = mock_build_pr_data_from()

        first_file = pr_data.files_changed[0]
        assert "UrlShortenerController" in first_file.filename
        assert first_file.status == "modified"
        assert first_file.additions == 7
        assert first_file.deletions == 0

    def test_mock_pr_data_is_valid_pydantic_model(self):
        """Test that mock PR data is a valid Pydantic model."""
        pr_data = mock_build_pr_data_from()

        # Should not raise validation error
        assert pr_data.pr_metadata is not None
        assert pr_data.files_changed is not None
        assert pr_data.linked_issues is not None


class TestDataRetrieverNode:
    """Tests for data_retriever_node async function."""

    def create_mock_runtime(self):
        """Create a mock runtime object."""
        mock_runtime = Mock(spec=Runtime)
        mock_runtime.context = Mock(spec=ContextRepoInfo)
        mock_runtime.context.user_name = "testuser"
        mock_runtime.context.repository = "testrepo"
        mock_runtime.context.pull_number = 1
        return mock_runtime

    @pytest.mark.asyncio
    @patch('app.agents.nodes.data_retriever_node.settings')
    async def test_data_retriever_node_mock_mode(self, mock_settings):
        """Test data_retriever_node returns mock data in mock mode."""
        mock_settings.IS_MOCK = True
        mock_runtime = self.create_mock_runtime()

        state = PRState()
        result = await data_retriever_node(state, mock_runtime)

        assert "pr_data" in result
        assert result["pr_data"].pr_metadata.title == "Feature/unregister"

    @pytest.mark.asyncio
    @patch('app.agents.nodes.data_retriever_node.settings')
    @patch('app.agents.nodes.data_retriever_node.data_retriever')
    async def test_data_retriever_node_real_mode(self, mock_retriever, mock_settings):
        """Test data_retriever_node calls data_retriever in non-mock mode."""
        mock_settings.IS_MOCK = False
        mock_runtime = self.create_mock_runtime()

        mock_pr_data = mock_build_pr_data_from()
        mock_retriever.return_value = {"pr_data": mock_pr_data}

        state = PRState()
        result = await data_retriever_node(state, mock_runtime)

        assert "pr_data" in result
        mock_retriever.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.agents.nodes.data_retriever_node.settings')
    async def test_data_retriever_node_returns_dict(self, mock_settings):
        """Test that data_retriever_node returns a dictionary."""
        mock_settings.IS_MOCK = True
        mock_runtime = self.create_mock_runtime()

        state = PRState()
        result = await data_retriever_node(state, mock_runtime)

        assert isinstance(result, dict)
        assert "pr_data" in result


class TestDataRetriever:
    """Tests for data_retriever async function."""

    def create_mock_runtime(self):
        """Create a mock runtime object."""
        mock_runtime = Mock(spec=Runtime)
        mock_runtime.context = Mock(spec=ContextRepoInfo)
        mock_runtime.context.user_name = "octocat"
        mock_runtime.context.repository = "Hello-World"
        mock_runtime.context.pull_number = 1
        return mock_runtime

    @pytest.mark.asyncio
    @patch('app.agents.nodes.data_retriever_node.Github')
    async def test_data_retriever_fetches_from_github(self, mock_github_class):
        """Test data_retriever fetches PR data from GitHub."""
        mock_runtime = self.create_mock_runtime()

        # Setup mock GitHub objects
        mock_github = Mock()
        mock_github_class.return_value = mock_github

        mock_user = Mock()
        mock_github.get_user.return_value = mock_user

        mock_repo = Mock()
        mock_user.get_repo.return_value = mock_repo

        mock_pr = Mock()
        mock_pr.title = "Test PR"
        mock_pr.body = ""
        mock_pr.user.login = "testuser"
        mock_pr.base.ref = "main"
        mock_pr.labels = []
        mock_pr.get_files.return_value = []

        mock_repo.get_pull.return_value = mock_pr

        result = await data_retriever(mock_runtime)

        assert "pr_data" in result
        mock_github_class.assert_called_once()
        mock_github.get_user.assert_called_once_with("octocat")
        mock_user.get_repo.assert_called_once_with("Hello-World")
        mock_repo.get_pull.assert_called_once_with(number=1)

    @pytest.mark.asyncio
    @patch('app.agents.nodes.data_retriever_node.Github')
    async def test_data_retriever_calls_build_pr_data(self, mock_github_class):
        """Test that data_retriever uses build_pr_data_from."""
        mock_runtime = self.create_mock_runtime()

        # Setup mock GitHub objects with a realistic PR
        mock_github = Mock()
        mock_github_class.return_value = mock_github

        mock_user = Mock()
        mock_github.get_user.return_value = mock_user

        mock_repo = Mock()
        mock_user.get_repo.return_value = mock_repo

        mock_pr = Mock()
        mock_pr.title = "Feature: Add authentication"
        mock_pr.body = "Implements OAuth2 login"
        mock_pr.user.login = "developer"
        mock_pr.base.ref = "develop"
        mock_pr.labels = []
        mock_pr.get_files.return_value = []

        mock_repo.get_pull.return_value = mock_pr

        result = await data_retriever(mock_runtime)

        assert result["pr_data"].pr_metadata.title == "Feature: Add authentication"
        assert result["pr_data"].pr_metadata.author == "developer"
