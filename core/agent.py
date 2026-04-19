"""
CareerAI - Claude API通信コアロジック
プロンプトキャッシュ（cache_control）を使ってシステムプロンプトをキャッシュし、コストを最適化する。
"""

import os
import anthropic
from core.prompts import SYSTEM_PROMPT

# シングルトンクライアント（起動時に一度だけ初期化）
_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    """Anthropicクライアントをシングルトンで返す"""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY が設定されていません。"
                "環境変数または Streamlit Secrets に設定してください。"
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def chat(messages: list[dict]) -> str:
    """
    無料版: Claude Haiku を使ったキャリア相談。
    システムプロンプトに cache_control を付けてトークンコストを削減する。

    Args:
        messages: [{"role": "user"|"assistant", "content": "..."}] の会話履歴

    Returns:
        AIの応答テキスト
    """
    client = get_client()

    system = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},  # システムプロンプトをキャッシュ
        }
    ]

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=system,
        messages=messages,
    )

    return response.content[0].text


def chat_premium(messages: list[dict]) -> str:
    """
    有料版: Claude Sonnet を使った高精度キャリア相談。
    システムプロンプトに cache_control を付けてトークンコストを削減する。

    Args:
        messages: [{"role": "user"|"assistant", "content": "..."}] の会話履歴

    Returns:
        AIの応答テキスト
    """
    client = get_client()

    system = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},  # システムプロンプトをキャッシュ
        }
    ]

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2048,
        system=system,
        messages=messages,
    )

    return response.content[0].text
