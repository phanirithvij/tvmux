"""Tests for api_client module."""
import json
from unittest.mock import Mock, patch
import pytest
import requests
from pydantic import BaseModel

from tvmux.api_client import APIError, api_call


class ResponseModel(BaseModel):
    """Test model for API responses."""
    name: str
    value: int


class RequestModel(BaseModel):
    """Test model for API requests."""
    action: str
    count: int


def test_api_error_creation():
    """Test creating APIError with status code and detail."""
    error = APIError(404, "Not found")

    assert error.status_code == 404
    assert error.detail == "Not found"
    assert str(error) == "API error 404: Not found"


def test_api_error_inheritance():
    """Test that APIError inherits from Exception."""
    error = APIError(500, "Server error")

    assert isinstance(error, Exception)


def test_api_error_with_empty_detail():
    """Test APIError with empty detail."""
    error = APIError(400, "")

    assert error.status_code == 400
    assert error.detail == ""
    assert str(error) == "API error 400: "


class TestAPICall:
    """Tests for api_call function."""

    @patch('requests.Session')
    def test_api_call_success_with_model(self, mock_session_class):
        """Test successful API call with response model."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"name": "test", "value": 42}'

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Make call
        result = api_call(
            "http://localhost:8000",
            "GET",
            "/test",
            response_model=ResponseModel
        )

        # Verify
        assert isinstance(result, ResponseModel)
        assert result.name == "test"
        assert result.value == 42

        mock_session.request.assert_called_once_with("GET", "http://localhost:8000/test")

    @patch('requests.Session')
    def test_api_call_success_without_model(self, mock_session_class):
        """Test successful API call without response model."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"result": "success"}'
        mock_response.json.return_value = {"result": "success"}

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Make call
        result = api_call("http://localhost:8000", "GET", "/test")

        # Verify
        assert result == {"result": "success"}

    @patch('requests.Session')
    def test_api_call_with_request_data(self, mock_session_class):
        """Test API call with request data."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.content = b'{"id": 123}'
        mock_response.json.return_value = {"id": 123}

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Make call with data
        request_data = RequestModel(action="create", count=5)
        result = api_call(
            "http://localhost:8000",
            "POST",
            "/items",
            data=request_data
        )

        # Verify
        assert result == {"id": 123}
        mock_session.request.assert_called_once_with(
            "POST",
            "http://localhost:8000/items",
            json={"action": "create", "count": 5}
        )

    @patch('requests.Session')
    def test_api_call_empty_response(self, mock_session_class):
        """Test API call with empty response."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.content = b''

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Make call
        result = api_call("http://localhost:8000", "DELETE", "/item/123")

        # Verify
        assert result == {}

    @patch('requests.Session')
    def test_api_call_404_error(self, mock_session_class):
        """Test API call with 404 error."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"detail": "Item not found"}

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Make call and expect error
        with pytest.raises(APIError) as exc_info:
            api_call("http://localhost:8000", "GET", "/item/999")

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Item not found"

    @patch('requests.Session')
    def test_api_call_500_error_with_text(self, mock_session_class):
        """Test API call with 500 error and text response."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = Exception("Not JSON")
        mock_response.text = "Internal Server Error"

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Make call and expect error
        with pytest.raises(APIError) as exc_info:
            api_call("http://localhost:8000", "POST", "/broken")

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Internal Server Error"

    @patch('requests.Session')
    def test_api_call_network_error(self, mock_session_class):
        """Test API call with network error."""
        mock_session = Mock()
        mock_session.request.side_effect = requests.ConnectionError("Connection failed")
        mock_session_class.return_value = mock_session

        # Make call and expect error
        with pytest.raises(APIError) as exc_info:
            api_call("http://localhost:8000", "GET", "/test")

        assert exc_info.value.status_code == 0
        assert "Connection failed" in exc_info.value.detail

    @patch('requests.Session')
    def test_api_call_url_building(self, mock_session_class):
        """Test URL building with various path formats."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"ok": true}'
        mock_response.json.return_value = {"ok": True}

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Test with leading slash
        api_call("http://localhost:8000", "GET", "/api/test")
        mock_session.request.assert_called_with("GET", "http://localhost:8000/api/test")

        # Test without leading slash
        api_call("http://localhost:8000", "GET", "api/test")
        mock_session.request.assert_called_with("GET", "http://localhost:8000/api/test")

        # Test with trailing slash on base URL
        api_call("http://localhost:8000/", "GET", "/api/test")
        mock_session.request.assert_called_with("GET", "http://localhost:8000/api/test")

    @patch('requests.Session')
    def test_api_call_session_configuration(self, mock_session_class):
        """Test that session is configured correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{}'
        mock_response.json.return_value = {}

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Make call
        api_call("http://localhost:8000", "GET", "/test")

        # Verify session configuration
        assert mock_session.max_redirects == 10

    @patch('requests.Session')
    def test_api_call_error_without_detail(self, mock_session_class):
        """Test API error when response has no detail or text."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.side_effect = Exception("Not JSON")
        mock_response.text = ""

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Make call and expect error
        with pytest.raises(APIError) as exc_info:
            api_call("http://localhost:8000", "GET", "/test")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "HTTP 400"

    @patch('requests.Session')
    def test_api_call_json_validation_error(self, mock_session_class):
        """Test handling of JSON validation errors in response model."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"invalid": "data"}'

        mock_session = Mock()
        mock_session.request.return_value = mock_response
        mock_session_class.return_value = mock_session

        # Make call with model that expects different structure
        with pytest.raises(Exception):  # Pydantic validation error
            api_call(
                "http://localhost:8000",
                "GET",
                "/test",
                response_model=ResponseModel
            )
