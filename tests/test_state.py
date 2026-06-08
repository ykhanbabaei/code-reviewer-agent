"""Unit tests for state module."""
import pytest
from pydantic import ValidationError

from app.agents.state import (
    PRState,
    PRMetadata,
    ChangedFile,
    PRData,
    ReviewComment
)


class TestPRMetadata:
    """Tests for PRMetadata model."""

    def test_pr_metadata_creation(self):
        """Test creating a valid PRMetadata."""
        metadata = PRMetadata(
            title="Add feature X",
            description="This PR adds feature X",
            author="developer",
            base_branch="main"
        )

        assert metadata.title == "Add feature X"
        assert metadata.description == "This PR adds feature X"
        assert metadata.author == "developer"
        assert metadata.base_branch == "main"
        assert metadata.labels == []

    def test_pr_metadata_with_labels(self):
        """Test PRMetadata with labels."""
        metadata = PRMetadata(
            title="Fix bug",
            description="Fixes critical bug",
            author="developer",
            base_branch="main",
            labels=["bug", "urgent"]
        )

        assert metadata.labels == ["bug", "urgent"]

    def test_pr_metadata_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            PRMetadata(title="Test")  # Missing required fields


class TestChangedFile:
    """Tests for ChangedFile model."""

    def test_changed_file_creation(self):
        """Test creating a valid ChangedFile."""
        file = ChangedFile(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=5,
            patch="@@ -1,5 +1,8 @@ ..."
        )

        assert file.filename == "src/main.py"
        assert file.status == "modified"
        assert file.additions == 10
        assert file.deletions == 5
        assert file.patch == "@@ -1,5 +1,8 @@ ..."

    def test_changed_file_statuses(self):
        """Test all valid file statuses."""
        for status in ["added", "modified", "deleted", "renamed"]:
            file = ChangedFile(
                filename="test.py",
                status=status,
                additions=0,
                deletions=0,
                patch=""
            )
            assert file.status == status

    def test_changed_file_invalid_status(self):
        """Test that invalid status is rejected."""
        with pytest.raises(ValidationError):
            ChangedFile(
                filename="test.py",
                status="invalid_status",
                additions=0,
                deletions=0,
                patch=""
            )

    def test_changed_file_additions_deletions_non_negative(self):
        """Test that additions and deletions must be non-negative."""
        with pytest.raises(ValidationError):
            ChangedFile(
                filename="test.py",
                status="modified",
                additions=-1,
                deletions=5,
                patch=""
            )

        with pytest.raises(ValidationError):
            ChangedFile(
                filename="test.py",
                status="modified",
                additions=5,
                deletions=-1,
                patch=""
            )

    def test_changed_file_with_full_content(self):
        """Test ChangedFile with full_content URL."""
        file = ChangedFile(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=5,
            patch="@@ ... @@",
            full_content="https://api.github.com/repos/.../contents/main.py"
        )

        assert file.full_content == "https://api.github.com/repos/.../contents/main.py"

    def test_changed_file_full_content_optional(self):
        """Test that full_content is optional."""
        file = ChangedFile(
            filename="src/main.py",
            status="modified",
            additions=10,
            deletions=5,
            patch="@@ ... @@"
        )

        assert file.full_content is None


class TestReviewComment:
    """Tests for ReviewComment model."""

    def test_review_comment_creation(self):
        """Test creating a valid ReviewComment."""
        comment = ReviewComment(
            file_path="src/main.py",
            line_number=42,
            comment="This function needs better error handling"
        )

        assert comment.file_path == "src/main.py"
        assert comment.line_number == 42
        assert comment.comment == "This function needs better error handling"
        assert comment.severity is None

    def test_review_comment_with_severity(self):
        """Test ReviewComment with severity level."""
        for severity in ["info", "warning", "error"]:
            comment = ReviewComment(
                file_path="src/main.py",
                line_number=10,
                comment="Test comment",
                severity=severity
            )
            assert comment.severity == severity

    def test_review_comment_without_line_number(self):
        """Test ReviewComment without line_number."""
        comment = ReviewComment(
            file_path="src/main.py",
            comment="File-level comment"
        )

        assert comment.line_number is None

    def test_review_comment_invalid_severity(self):
        """Test that invalid severity is rejected."""
        with pytest.raises(ValidationError):
            ReviewComment(
                file_path="src/main.py",
                line_number=10,
                comment="Test",
                severity="invalid"
            )


class TestPRData:
    """Tests for PRData model."""

    def test_pr_data_creation(self):
        """Test creating a valid PRData."""
        metadata = PRMetadata(
            title="Test PR",
            description="Test",
            author="dev",
            base_branch="main"
        )

        pr_data = PRData(pr_metadata=metadata)

        assert pr_data.pr_metadata == metadata
        assert pr_data.files_changed == []
        assert pr_data.linked_issues == []
        assert pr_data.review_comments == []

    def test_pr_data_with_files(self):
        """Test PRData with files_changed."""
        metadata = PRMetadata(
            title="Test PR",
            description="Test",
            author="dev",
            base_branch="main"
        )

        files = [
            ChangedFile(
                filename="src/main.py",
                status="modified",
                additions=10,
                deletions=5,
                patch="@@ ... @@"
            )
        ]

        pr_data = PRData(pr_metadata=metadata, files_changed=files)

        assert len(pr_data.files_changed) == 1
        assert pr_data.files_changed[0].filename == "src/main.py"

    def test_pr_data_with_linked_issues(self):
        """Test PRData with linked_issues."""
        metadata = PRMetadata(
            title="Test PR",
            description="Test",
            author="dev",
            base_branch="main"
        )

        pr_data = PRData(
            pr_metadata=metadata,
            linked_issues=["#123", "#456"]
        )

        assert pr_data.linked_issues == ["#123", "#456"]

    def test_pr_data_with_review_comments(self):
        """Test PRData with review_comments."""
        metadata = PRMetadata(
            title="Test PR",
            description="Test",
            author="dev",
            base_branch="main"
        )

        comment = ReviewComment(
            file_path="src/main.py",
            line_number=42,
            comment="Good fix"
        )

        pr_data = PRData(
            pr_metadata=metadata,
            review_comments=[comment]
        )

        assert len(pr_data.review_comments) == 1
        assert pr_data.review_comments[0].comment == "Good fix"


class TestPRState:
    """Tests for PRState model."""

    def test_pr_state_creation_empty(self):
        """Test creating an empty PRState."""
        state = PRState()

        assert state.pr_data is None
        assert state.files_to_review is None
        assert state.skipped_files is None
        assert state.current_file_index == 0
        assert state.file_reviews is None
        assert state.summary is None
        assert state.approval_recommendation is None
        assert state.all_issues is None
        assert state.error is None

    def test_pr_state_with_data(self):
        """Test creating PRState with data."""
        pr_metadata = PRMetadata(
            title="Test PR",
            description="Test",
            author="dev",
            base_branch="main"
        )

        files = [
            ChangedFile(
                filename="src/main.py",
                status="modified",
                additions=10,
                deletions=5,
                patch="@@ ... @@"
            )
        ]

        pr_data = PRData(pr_metadata=pr_metadata, files_changed=files)

        state = PRState(
            pr_data=pr_data,
            files_to_review=files,
            current_file_index=0
        )

        assert state.pr_data == pr_data
        assert state.files_to_review == files
        assert state.current_file_index == 0

    def test_pr_state_current_file_index_non_negative(self):
        """Test that current_file_index must be non-negative."""
        with pytest.raises(ValidationError):
            PRState(current_file_index=-1)

    def test_pr_state_accumulates_file_reviews(self):
        """Test that file_reviews can be accumulated."""
        state = PRState(
            file_reviews=[
                {"file": "src/main.py", "review": {"issues": []}},
                {"file": "src/utils.py", "review": {"issues": []}}
            ]
        )

        assert len(state.file_reviews) == 2

    def test_pr_state_accumulates_all_issues(self):
        """Test that all_issues can be accumulated."""
        state = PRState(
            all_issues=[
                {"file": "src/main.py", "issue": "Bug in line 42"},
                {"file": "src/utils.py", "issue": "Security issue"}
            ]
        )

        assert len(state.all_issues) == 2

    def test_pr_state_with_error(self):
        """Test PRState with error field."""
        state = PRState(
            error="Failed to process PR"
        )

        assert state.error == "Failed to process PR"

    def test_pr_state_with_skipped_files(self):
        """Test PRState with skipped_files."""
        state = PRState(
            skipped_files=["package.json", "README.md"]
        )

        assert state.skipped_files == ["package.json", "README.md"]
