"""
Gumroad ライセンスキー検証モジュール
有料版のプレミアムアクセスを制御する。
"""

import requests

GUMROAD_API_URL = "https://api.gumroad.com/v2/licenses/verify"
PRODUCT_PERMALINK = "career-ai-monthly"  # Gumroadの商品パーマリンク（agenta31.gumroad.com/l/career-ai-monthly）


def verify_license(license_key: str) -> dict:
    """
    Gumroad ライセンスキーを検証する。

    Args:
        license_key: ユーザーが入力したライセンスキー

    Returns:
        {
            "valid": bool,
            "email": str | None,
            "error": str | None
        }
    """
    if not license_key or not license_key.strip():
        return {"valid": False, "email": None, "error": "ライセンスキーを入力してください"}

    try:
        response = requests.post(
            GUMROAD_API_URL,
            data={
                "product_permalink": PRODUCT_PERMALINK,
                "license_key": license_key.strip(),
                "increment_uses_count": "false",
            },
            timeout=5,
        )

        data = response.json()

        if data.get("success") and not data["purchase"].get("refunded"):
            return {
                "valid": True,
                "email": data["purchase"]["email"],
                "error": None,
            }
        else:
            return {
                "valid": False,
                "email": None,
                "error": "無効なライセンスキーです。Gumroadのメールをご確認ください。",
            }

    except requests.Timeout:
        return {
            "valid": False,
            "email": None,
            "error": "認証サーバーに接続できません。しばらくしてから再試行してください。",
        }
    except Exception as e:
        return {
            "valid": False,
            "email": None,
            "error": f"認証エラー: {str(e)}",
        }
