"""
agent.py のユニットテスト
"""

import pytest
from unittest.mock import patch, MagicMock


def test_chat_returns_string():
    """chat() が文字列を返すことを確認"""
    with patch("core.agent._client") as mock_client:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="テストレスポンス")]
        mock_client.messages.create.return_value = mock_response

        from core.agent import chat

        result = chat([{"role": "user", "content": "テスト"}])
        assert isinstance(result, str)
        assert len(result) > 0


def test_chat_passes_messages_correctly():
    """messages が正しく Claude API に渡されることを確認"""
    messages = [
        {"role": "user", "content": "転職を考えています"},
        {"role": "assistant", "content": "具体的な状況を教えてください"},
        {"role": "user", "content": "経験5年でGoエンジニアです"},
    ]

    with patch("core.agent._client") as mock_client:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="回答")]
        mock_client.messages.create.return_value = mock_response

        from core.agent import chat

        chat(messages)

        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["messages"] == messages


def test_chat_uses_haiku_model():
    """無料版が claude-haiku-4-5 を使うことを確認"""
    with patch("core.agent._client") as mock_client:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="回答")]
        mock_client.messages.create.return_value = mock_response

        from core.agent import chat

        chat([{"role": "user", "content": "テスト"}])

        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["model"] == "claude-haiku-4-5"


def test_chat_premium_uses_sonnet_model():
    """有料版が claude-sonnet-4-5 を使うことを確認"""
    with patch("core.agent._client") as mock_client:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="詳細な回答")]
        mock_client.messages.create.return_value = mock_response

        from core.agent import chat_premium

        chat_premium([{"role": "user", "content": "テスト"}])

        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["model"] == "claude-sonnet-4-5"


def test_chat_system_prompt_has_cache_control():
    """システムプロンプトに cache_control が設定されていることを確認"""
    with patch("core.agent._client") as mock_client:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="回答")]
        mock_client.messages.create.return_value = mock_response

        from core.agent import chat

        chat([{"role": "user", "content": "テスト"}])

        call_args = mock_client.messages.create.call_args
        system = call_args.kwargs["system"]
        assert len(system) == 1
        assert system[0]["cache_control"] == {"type": "ephemeral"}


def test_get_client_raises_without_api_key():
    """ANTHROPIC_API_KEY が未設定の場合に ValueError が発生することを確認"""
    import core.agent as agent_module
    original_client = agent_module._client
    agent_module._client = None

    try:
        with patch.dict("os.environ", {}, clear=True):
            # ANTHROPIC_API_KEY を環境変数から除去
            import os
            os.environ.pop("ANTHROPIC_API_KEY", None)

            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                agent_module.get_client()
    finally:
        agent_module._client = original_client
