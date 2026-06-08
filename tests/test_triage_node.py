"""Unit tests for triage_node module."""
import pytest
from unittest.mock import Mock, MagicMock
from langgraph.runtime import Runtime

from app.agents.state import PRState, PRData, PRMetadata, ChangedFile
from app.agents.context import ContextRepoInfo
from app.agents.nodes.triage_node import triage_node


class TestTriageNode:
    """Tests for triage_node function."""

    def create_mock_runtime(self):
        """Create a mock runtime object."""
        mock_runtime = Mock(spec=Runtime)
        mock_runtime.context = Mock(spec=ContextRepoInfo)
        mock_runtime.context.user_name = "testuser"
        mock_runtime.context.repository = "testrepo"
        mock_runtime.context.pull_number = 1
        return mock_runtime

    def test_triage_filters_lock_files(self):
        """Test that .lock files are filtered out."""
        mock_runtime = self.create_mock_runtime()

        pr_metadata = PRMetadata(
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main"
        )

        files = [
            ChangedFile(
                filename="package-lock.json",
                status="modified",
                additions=100,
                deletions=50,
                patch="@@ ... @@"
            ),
            ChangedFile(
                filename="src/main.py",
                status="modified",
                additions=10,
                deletions=5,
                patch="@@ ... @@"
            ),
        ]

        pr_data = PRData(pr_metadata=pr_metadata, files_changed=files)
        state = PRState(pr_data=pr_data)

        result = triage_node(state, mock_runtime)

        assert len(result["files_to_review"]) == 1
        assert result["files_to_review"][0].filename == "src/main.py"

    def test_triage_filters_markdown_files(self):
        """Test that .md files are filtered out."""
        mock_runtime = self.create_mock_runtime()

        pr_metadata = PRMetadata(
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main"
        )

        files = [
            ChangedFile(
                filename="README.md",
                status="modified",
                additions=50,
                deletions=10,
                patch="@@ ... @@"
            ),
            ChangedFile(
                filename="src/utils.py",
                status="modified",
                additions=20,
                deletions=5,
                patch="@@ ... @@"
            ),
        ]

        pr_data = PRData(pr_metadata=pr_metadata, files_changed=files)
        state = PRState(pr_data=pr_data)

        result = triage_node(state, mock_runtime)

        assert len(result["files_to_review"]) == 1
        assert result["files_to_review"][0].filename == "src/utils.py"

    def test_triage_filters_json_files(self):
        """Test that .json files are filtered out."""
        mock_runtime = self.create_mock_runtime()

        pr_metadata = PRMetadata(
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main"
        )

        files = [
            ChangedFile(
                filename="config.json",
                status="modified",
                additions=10,
                deletions=2,
                patch="@@ ... @@"
            ),
            ChangedFile(
                filename="src/handler.py",
                status="modified",
                additions=15,
                deletions=3,
                patch="@@ ... @@"
            ),
        ]

        pr_data = PRData(pr_metadata=pr_metadata, files_changed=files)
        state = PRState(pr_data=pr_data)

        result = triage_node(state, mock_runtime)

        assert len(result["files_to_review"]) == 1
        assert result["files_to_review"][0].filename == "src/handler.py"

    def test_triage_filters_small_changes(self):
        """Test that files with small changes (≤2 lines) are filtered out."""
        mock_runtime = self.create_mock_runtime()

        pr_metadata = PRMetadata(
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main"
        )

        files = [
            ChangedFile(
                filename="src/small_change.py",
                status="modified",
                additions=1,
                deletions=1,
                patch="@@ ... @@"
            ),
            ChangedFile(
                filename="src/large_change.py",
                status="modified",
                additions=10,
                deletions=5,
                patch="@@ ... @@"
            ),
        ]

        pr_data = PRData(pr_metadata=pr_metadata, files_changed=files)
        state = PRState(pr_data=pr_data)

        result = triage_node(state, mock_runtime)

        assert len(result["files_to_review"]) == 1
        assert result["files_to_review"][0].filename == "src/large_change.py"

    def test_triage_includes_exactly_3_line_changes(self):
        """Test that files with exactly 3 lines of changes are included (> 2)."""
        mock_runtime = self.create_mock_runtime()

        pr_metadata = PRMetadata(
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main"
        )

        files = [
            ChangedFile(
                filename="src/change.py",
                status="modified",
                additions=2,
                deletions=1,
                patch="@@ ... @@"
            ),
        ]

        pr_data = PRData(pr_metadata=pr_metadata, files_changed=files)
        state = PRState(pr_data=pr_data)

        result = triage_node(state, mock_runtime)

        assert len(result["files_to_review"]) == 1
        assert result["files_to_review"][0].filename == "src/change.py"

    def test_triage_returns_current_index_zero(self):
        """Test that current_file_index is reset to 0."""
        mock_runtime = self.create_mock_runtime()

        pr_metadata = PRMetadata(
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main"
        )

        files = [
            ChangedFile(
                filename="src/file.py",
                status="modified",
                additions=10,
                deletions=5,
                patch="@@ ... @@"
            ),
        ]

        pr_data = PRData(pr_metadata=pr_metadata, files_changed=files)
        state = PRState(pr_data=pr_data, current_file_index=5)  # Start with non-zero index

        result = triage_node(state, mock_runtime)

        assert result["current_file_index"] == 0

    def test_triage_all_files_filtered(self):
        """Test when all files are filtered out (config-only PR)."""
        mock_runtime = self.create_mock_runtime()

        pr_metadata = PRMetadata(
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main"
        )

        files = [
            ChangedFile(
                filename="package.json",
                status="modified",
                additions=1,
                deletions=0,
                patch="@@ ... @@"
            ),
            ChangedFile(
                filename="README.md",
                status="modified",
                additions=5,
                deletions=1,
                patch="@@ ... @@"
            ),
        ]

        pr_data = PRData(pr_metadata=pr_metadata, files_changed=files)
        state = PRState(pr_data=pr_data)

        result = triage_node(state, mock_runtime)

        assert len(result["files_to_review"]) == 0

    def test_triage_mixed_file_types(self):
        """Test triage with mixed file types."""
        mock_runtime = self.create_mock_runtime()

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
                additions=20,
                deletions=10,
                patch="@@ ... @@"
            ),
            ChangedFile(
                filename="README.md",
                status="modified",
                additions=5,
                deletions=2,
                patch="@@ ... @@"
            ),
            ChangedFile(
                filename="src/utils.js",
                status="added",
                additions=30,
                deletions=0,
                patch="@@ ... @@"
            ),
            ChangedFile(
                filename="package-lock.json",
                status="modified",
                additions=100,
                deletions=50,
                patch="@@ ... @@"
            ),
            ChangedFile(
                filename="config.json",
                status="modified",
                additions=2,
                deletions=1,
                patch="@@ ... @@"
            ),
        ]

        pr_data = PRData(pr_metadata=pr_metadata, files_changed=files)
        state = PRState(pr_data=pr_data)

        result = triage_node(state, mock_runtime)

        assert len(result["files_to_review"]) == 2
        filenames = {f.filename for f in result["files_to_review"]}
        assert filenames == {"src/main.py", "src/utils.js"}

    def test_triage_preserves_file_data(self):
        """Test that file data is preserved during triage."""
        mock_runtime = self.create_mock_runtime()

        pr_metadata = PRMetadata(
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main"
        )

        patch_content = "@@ -1,5 +1,8 @@ ... @@"
        files = [
            ChangedFile(
                filename="src/main.py",
                status="modified",
                additions=20,
                deletions=10,
                patch=patch_content,
                full_content="https://api.github.com/repos/.../contents/main.py"
            ),
        ]

        pr_data = PRData(pr_metadata=pr_metadata, files_changed=files)
        state = PRState(pr_data=pr_data)

        result = triage_node(state, mock_runtime)

        reviewed_file = result["files_to_review"][0]
        assert reviewed_file.patch == patch_content
        assert reviewed_file.full_content == "https://api.github.com/repos/.../contents/main.py"
        assert reviewed_file.status == "modified"
