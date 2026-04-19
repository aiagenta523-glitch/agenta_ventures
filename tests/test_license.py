"""
license.py のユニットテスト
"""

import pytest
from unittest.mock import patch
import requests
from core.license import verify_license


def test_valid_license():
    """有効なライセンスキーで valid=True が返ることを確認"""
    mock_response_data = {
        "success": True,
        "purchase": {
            "email": "test@example.com",
            "refunded": False,
        },
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = mock_response_data
        result = verify_license("VALID-LICENSE-KEY-1234")

        assert result["valid"] is True
        assert result["email"] == "test@example.com"
        assert result["error"] is None


def test_invalid_license():
    """無効なライセンスキーで valid=False が返ることを確認"""
    mock_response_data = {"success": False}

    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = mock_response_data
        result = verify_license("INVALID-KEY")

        assert result["valid"] is False
        assert result["email"] is None
        assert result["error"] is not None


def test_refunded_license():
    """返金済みライセンスで valid=False が返ることを確認"""
    mock_response_data = {
        "success": True,
        "purchase": {
            "email": "refunded@example.com",
            "refunded": True,
        },
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = mock_response_data
        result = verify_license("REFUNDED-KEY-1234")

        assert result["valid"] is False


def test_timeout_handling():
    """タイムアウト時にエラーメッセージが返ることを確認"""
    with patch("requests.post") as mock_post:
        mock_post.side_effect = requests.Timeout()
        result = verify_license("ANY-KEY")

        assert result["valid"] is False
        assert "接続" in result["error"]


def test_empty_license_key():
    """空文字・空白のみのキーで valid=False が返ることを確認"""
    result = verify_license("")
    assert result["valid"] is False

    result = verify_license("   ")
    assert result["valid"] is False


def test_license_key_is_stripped():
    """ライセンスキーの前後の空白がトリムされてAPIに渡されることを確認"""
    mock_response_data = {
        "success": True,
        "purchase": {"email": "test@example.com", "refunded": False},
    }

    with patch("requests.post") as mock_post:
        mock_post.return_value.json.return_value = mock_response_data
        verify_license("  VALID-KEY-WITH-SPACES  ")

        call_args = mock_post.call_args
        assert call_args.kwargs["data"]["license_key"] == "VALID-KEY-WITH-SPACES"
