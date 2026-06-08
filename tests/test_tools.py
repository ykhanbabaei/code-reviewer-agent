"""Unit tests for tools module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from langchain.messages import ToolMessage
from langchain.tools.tool_node import ToolCallRequest

from app.agents.tools import (
    full_file_content_provider,
    handle_tool_errors,
    _tool_call_counts
)


class TestFullFileContentProvider:
    """Tests for full_file_content_provider tool."""

    @patch('app.agents.tools.requests.get')
    def test_fetch_full_file_content_success(self, mock_get):
        """Test successful fetching of full file content."""
        # Mock the API responses
        mock_response_1 = Mock()
        mock_response_1.json.return_value = {
            "download_url": "https://raw.githubusercontent.com/user/repo/main/file.py"
        }

        mock_response_2 = Mock()
        mock_response_2.text = "def hello():\n    print('Hello, World!')"

        mock_get.side_effect = [mock_response_1, mock_response_2]

        # Call the tool
        result = full_file_content_provider.invoke(input=
            "https://api.github.com/repos/user/repo/contents/file.py"
        )

        # Assertions
        assert result == "def hello():\n    print('Hello, World!')"
        assert mock_get.call_count == 2

    @patch('app.agents.tools.requests.get')
    def test_fetch_full_file_content_network_error(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = Exception("Network error")

        with pytest.raises(Exception, match="Network error"):
            full_file_content_provider.invoke(input="https://api.github.com/repos/user/repo/contents/file.py")

    @patch('app.agents.tools.requests.get')
    def test_fetch_full_file_content_invalid_json(self, mock_get):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")

        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="Invalid JSON"):
            full_file_content_provider.invoke(input="https://api.github.com/repos/user/repo/contents/file.py")

    @patch('app.agents.tools.requests.get')
    def test_fetch_full_file_content_missing_download_url(self, mock_get):
        """Test handling when download_url is missing in response."""
        mock_response = Mock()
        mock_response.json.return_value = {"name": "file.py"}

        mock_get.return_value = mock_response

        with pytest.raises(KeyError):
            full_file_content_provider.invoke(input="https://api.github.com/repos/user/repo/contents/file.py")


class TestHandleToolErrors:
    """Tests for handle_tool_errors middleware."""

    def setup_method(self):
        """Clear tool call counts before each test."""
        _tool_call_counts.clear()



