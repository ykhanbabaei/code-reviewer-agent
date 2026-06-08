"""Comprehensive unit tests for file_reviewer_node module."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from langgraph.runtime import Runtime
from langgraph.types import Command

from app.agents.state import PRState, PRMetadata, ChangedFile, PRData
from app.agents.context import ContextRepoInfo
from app.agents.nodes.file_reviewer_node import (
    file_reviewer_node,
    build_prompt,
    FileReview,
    MOCK_INVOKE,
)


class TestFileReviewerNode:
    """Tests for file_reviewer_node async function."""

    def create_mock_runtime(self):
        """Create a mock runtime object."""
        mock_runtime = Mock(spec=Runtime)
        mock_runtime.context = Mock(spec=ContextRepoInfo)
        mock_runtime.context.user_name = "testuser"
        mock_runtime.context.repository = "testrepo"
        mock_runtime.context.pull_number = 1
        return mock_runtime

    def create_base_state(self):
        """Create a base PR state for testing."""
        pr_metadata = PRMetadata(
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main"
        )

        files = [
            ChangedFile(
                filename="src/main.py",
                status="modified",
                additions=10,
                deletions=5,
                patch="@@ -1,5 +1,10 @@ ..."
            ),
            ChangedFile(
                filename="src/utils.py",
                status="modified",
                additions=8,
                deletions=2,
                patch="@@ -1,3 +1,6 @@ ..."
            ),
        ]

        pr_data = PRData(pr_metadata=pr_metadata, files_changed=files)
        return PRState(
            pr_data=pr_data,
            files_to_review=files,
            current_file_index=0,
            file_reviews=[]
        )

    @pytest.mark.asyncio
    @patch('app.agents.nodes.file_reviewer_node.settings')
    async def test_file_reviewer_node_beyond_files_count(self, mock_settings):
        """Test that node returns goto=synthesizer_node when all files reviewed."""
        mock_settings.IS_MOCK = True
        mock_runtime = self.create_mock_runtime()

        state = self.create_base_state()
        state.current_file_index = 2  # Beyond 2 files
        state.files_to_review = state.files_to_review[:2]  # Only 2 files

        result = await file_reviewer_node(state, mock_runtime)

        assert result.goto == "synthesizer_node"

    @pytest.mark.asyncio
    @patch('app.agents.nodes.file_reviewer_node.settings')
    async def test_file_reviewer_node_mock_mode(self, mock_settings):
        """Test file_reviewer_node in mock mode."""
        mock_settings.IS_MOCK = True
        mock_runtime = self.create_mock_runtime()

        state = self.create_base_state()

        result = await file_reviewer_node(state, mock_runtime)

        assert result.goto == "file_reviewer_node"
        assert result.update is not None
        assert "file_reviews" in result.update
        assert result.update["current_file_index"] == 1

    @pytest.mark.asyncio
    @patch('app.agents.nodes.file_reviewer_node.settings')
    async def test_file_reviewer_node_increments_index(self, mock_settings):
        """Test that current_file_index is incremented."""
        mock_settings.IS_MOCK = True
        mock_runtime = self.create_mock_runtime()

        state = self.create_base_state()
        state.current_file_index = 0

        result = await file_reviewer_node(state, mock_runtime)

        assert result.update["current_file_index"] == 1

    @pytest.mark.asyncio
    @patch('app.agents.nodes.file_reviewer_node.settings')
    async def test_file_reviewer_node_returns_command(self, mock_settings):
        """Test that node returns a Command object."""
        mock_settings.IS_MOCK = True
        mock_runtime = self.create_mock_runtime()

        state = self.create_base_state()

        result = await file_reviewer_node(state, mock_runtime)

        assert isinstance(result, Command)
        assert result.update is not None

    @pytest.mark.asyncio
    @patch('app.agents.nodes.file_reviewer_node.settings')
    async def test_file_reviewer_node_accumulates_reviews(self, mock_settings):
        """Test that file reviews are accumulated."""
        mock_settings.IS_MOCK = True
        mock_runtime = self.create_mock_runtime()

        state = self.create_base_state()
        state.file_reviews = []

        result = await file_reviewer_node(state, mock_runtime)

        assert "file_reviews" in result.update
        assert len(result.update["file_reviews"]) > 0
        assert "file" in result.update["file_reviews"][0]
        assert "review" in result.update["file_reviews"][0]


    @pytest.mark.asyncio
    @patch('app.agents.nodes.file_reviewer_node.settings')
    async def test_file_reviewer_node_processes_correct_file(self, mock_settings):
        """Test that node processes the file at current_file_index."""
        mock_settings.IS_MOCK = True
        mock_runtime = self.create_mock_runtime()

        state = self.create_base_state()
        state.current_file_index = 1

        result = await file_reviewer_node(state, mock_runtime)

        # Check that the second file was reviewed
        assert result.update["file_reviews"][0]["file"] == "src/utils.py"


class TestBuildPrompt:
    """Tests for build_prompt function."""

    def test_build_prompt_includes_filename(self):
        """Test that prompt includes filename."""
        pr_meta = PRMetadata(
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main"
        )

        file = ChangedFile(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=5,
            patch="@@ ... @@"
        )

        prompt = build_prompt(file, pr_meta)

        assert "src/main.py" in prompt

    def test_build_prompt_includes_status(self):
        """Test that prompt includes file status."""
        pr_meta = PRMetadata(
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main"
        )

        file = ChangedFile(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=5,
            patch="@@ ... @@"
        )

        prompt = build_prompt(file, pr_meta)

        assert "modified" in prompt

    def test_build_prompt_includes_patch(self):
        """Test that prompt includes the patch."""
        pr_meta = PRMetadata(
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main"
        )

        patch_content = "@@ -1,5 +1,8 @@ def foo():\n+    pass"
        file = ChangedFile(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=5,
            patch=patch_content
        )

        prompt = build_prompt(file, pr_meta)

        assert patch_content in prompt

    def test_build_prompt_includes_pr_title(self):
        """Test that prompt includes PR title."""
        pr_meta = PRMetadata(
            title="Feature: Add authentication",
            description="Test description",
            author="testuser",
            base_branch="main"
        )

        file = ChangedFile(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=5,
            patch="@@ ... @@"
        )

        prompt = build_prompt(file, pr_meta)

        assert "Feature: Add authentication" in prompt

    def test_build_prompt_truncates_long_description(self):
        """Test that long descriptions are truncated to 300 chars."""
        long_description = "A" * 500
        pr_meta = PRMetadata(
            title="Test PR",
            description=long_description,
            author="testuser",
            base_branch="main"
        )

        file = ChangedFile(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=5,
            patch="@@ ... @@"
        )

        prompt = build_prompt(file, pr_meta)

        # Description should be truncated
        assert long_description[:300] in prompt
        assert long_description not in prompt

    def test_build_prompt_includes_full_content_url(self):
        """Test that prompt includes full_content URL when available."""
        pr_meta = PRMetadata(
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main"
        )

        full_content_url = "https://api.github.com/repos/.../contents/main.py"
        file = ChangedFile(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=5,
            patch="@@ ... @@",
            full_content=full_content_url
        )

        prompt = build_prompt(file, pr_meta)

        assert full_content_url in prompt

    def test_build_prompt_includes_tool_use_decision(self):
        """Test that prompt includes tool use decision guidance."""
        pr_meta = PRMetadata(
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main"
        )

        file = ChangedFile(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=5,
            patch="@@ ... @@"
        )

        prompt = build_prompt(file, pr_meta)

        assert "TOOL USE DECISION" in prompt
        assert "When in doubt" in prompt


class TestMockInvoke:
    """Tests for MOCK_INVOKE function."""

    def test_mock_invoke_returns_dict(self):
        """Test that MOCK_INVOKE returns a dictionary."""
        result = MOCK_INVOKE()

        assert isinstance(result, dict)
        assert "structured_response" in result

    def test_mock_invoke_structured_response_is_file_review(self):
        """Test that structured_response is a FileReview instance."""
        result = MOCK_INVOKE()

        assert isinstance(result["structured_response"], FileReview)

    def test_mock_invoke_review_has_expected_values(self):
        """Test that mock review has expected field values."""
        result = MOCK_INVOKE()

        review = result["structured_response"]
        assert review.filename == "src/user.py"
        assert review.issues == []
        assert review.severity == "clean"
        assert review.has_breaking_change is False
        assert review.needs_tests is False
