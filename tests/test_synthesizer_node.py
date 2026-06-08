"""Unit tests for synthesizer_node module."""
import pytest
from unittest.mock import Mock
from langgraph.runtime import Runtime

from app.agents.state import PRState
from app.agents.context import ContextRepoInfo
from app.agents.nodes.synthesizer_node import synthesizer_node


class TestSynthesizerNode:
    """Tests for synthesizer_node function."""

    def create_mock_runtime(self):
        """Create a mock runtime object."""
        mock_runtime = Mock(spec=Runtime)
        mock_runtime.context = Mock(spec=ContextRepoInfo)
        mock_runtime.context.user_name = "testuser"
        mock_runtime.context.repository = "testrepo"
        mock_runtime.context.pull_number = 1
        return mock_runtime

    def test_synthesizer_node_returns_dict(self):
        """Test that synthesizer_node returns a dictionary."""
        mock_runtime = self.create_mock_runtime()
        state = PRState(file_reviews=[])

        result = synthesizer_node(state, mock_runtime)

        assert isinstance(result, dict)

    def test_synthesizer_node_returns_required_keys(self):
        """Test that result contains required keys."""
        mock_runtime = self.create_mock_runtime()
        state = PRState(file_reviews=[])

        result = synthesizer_node(state, mock_runtime)

        assert "summary" in result
        assert "overall_severity" in result
        assert "all_issues" in result

    def test_synthesizer_node_empty_file_reviews(self):
        """Test synthesizer_node with empty file_reviews."""
        mock_runtime = self.create_mock_runtime()
        state = PRState(file_reviews=[])

        result = synthesizer_node(state, mock_runtime)

        assert result["all_issues"] == []

    def test_synthesizer_node_single_file_review_no_issues(self):
        """Test with single file review containing no issues."""
        mock_runtime = self.create_mock_runtime()

        file_review = {
            "file": "src/main.py",
            "review": {
                "filename": "src/main.py",
                "issues": [],
                "severity": "clean"
            }
        }

        state = PRState(file_reviews=[file_review])

        result = synthesizer_node(state, mock_runtime)

        assert result["all_issues"] == []


    def test_synthesizer_node_handles_missing_issues_key(self):
        """Test handling of file review without issues key."""
        mock_runtime = self.create_mock_runtime()

        file_review = {
            "file": "src/main.py",
            "review": {
                "filename": "src/main.py",
                "severity": "clean"
            }
        }

        state = PRState(file_reviews=[file_review])

        result = synthesizer_node(state, mock_runtime)

        assert result["all_issues"] == []

    def test_synthesizer_node_placeholder_values(self):
        """Test that placeholder values are returned for agent-dependent fields."""
        mock_runtime = self.create_mock_runtime()
        state = PRState(file_reviews=[])

        result = synthesizer_node(state, mock_runtime)

        assert result["summary"] == "agent call is required"
        assert result["overall_severity"] == "agent call is required"

