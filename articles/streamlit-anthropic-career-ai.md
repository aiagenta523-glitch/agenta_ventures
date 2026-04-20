---
title: "StreamlitとAnthropic APIでエンジニア向けキャリア相談AIを作った技術解説"
emoji: "🔧"
type: "tech"
topics: ["Streamlit", "Anthropic", "Python", "個人開発", "API"]
published: true
---


この記事では、エンジニア特化の転職相談AIサービス「CareerAI」の実装を技術的に解説します。

使用技術: Python 3.11 / Streamlit / Anthropic Python SDK / Gumroad API

完成物はGitHubで公開しています: [aiagenta523-glitch/agenta_ventures](https://github.com/aiagenta523-glitch/agenta_ventures)

---

## アーキテクチャの概要

```
career_ai/
├── app.py              # Streamlit エントリーポイント
├── core/
│   ├── agent.py        # Claude API通信ロジック（プロンプトキャッシュ使用）
│   ├── prompts.py      # システムプロンプト定義
│   └── license.py      # Gumroadライセンス認証
├── tests/
│   ├── test_agent.py
│   ├── test_license.py
│   └── test_prompts.py
├── .streamlit/
│   └── config.toml     # テーマ設定
└── requirements.txt
```

シンプルな設計です。Streamlitがフロントエンドを担い、`core/`以下に3つのモジュールを置きました。

---

## 1. プロンプトキャッシュの実装

CareerAIで最も気を使った部分がコスト最適化です。

会話型AIの課題は「毎回のリクエストでシステムプロンプトを送り続ける」こと。CareerAIのシステムプロンプトは約600トークンありますが、これを毎回課金すると積み重なります。

Anthropic APIには**プロンプトキャッシュ**機能があります。`cache_control: {"type": "ephemeral"}` をつけると、同一の内容を5分間キャッシュしてくれます。

### 実装: core/agent.py

```python
import os
import anthropic
from core.prompts import SYSTEM_PROMPT

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    """Anthropicクライアントをシングルトンで返す"""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY が設定されていません")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def chat(messages: list[dict]) -> str:
    """無料版: Claude Haikuでキャリア相談"""
    client = get_client()

    # システムプロンプトにcache_controlを付与
    system = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},  # ← ここがポイント
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
    """有料版: Claude Sonnetで高精度キャリア相談"""
    client = get_client()

    system = [
        {
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system,
        messages=messages,
    )

    return response.content[0].text
```

### キャッシュの効果

同一セッション内での2回目以降のリクエストでは、システムプロンプト部分のトークン費用が大幅削減されます。

| 状態 | input tokens課金対象 |
|------|---------------------|
| キャッシュなし | システムプロンプト + 会話履歴 + ユーザーメッセージ |
| キャッシュあり（ヒット時） | 会話履歴 + ユーザーメッセージのみ |

会話が続くほど節約効果が大きくなります。

### 注意点

- キャッシュのTTLは5分。5分以上ブラウザを放置するとキャッシュが切れる
- キャッシュミス時（初回・TTL切れ後）は通常課金される
- `beta` ヘッダーの指定が必要な場合があるので公式ドキュメントを確認すること

---

## 2. 無料/有料プランの切り分け

CareerAIは「月10回まで無料、それ以上は¥980のライセンスキーで解放」という設計です。

サーバーサイドにデータベースを持たずに実現する方法として**Gumroadのライセンス認証**を採用しました。

### 設計方針

```
ユーザー → Gumroadでライセンス購入 → キーをアプリに入力 → Gumroad APIで検証 → プレミアム解放
```

サーバーに状態を持たない。Gumroadがライセンス管理のSaaSになる。

### 実装: core/license.py

```python
import requests

GUMROAD_API_URL = "https://api.gumroad.com/v2/licenses/verify"
PRODUCT_PERMALINK = "career-ai-monthly"  # Gumroad商品パーマリンク


def verify_license(license_key: str) -> dict:
    """
    Gumroadライセンスキーを検証する。
    
    Returns:
        {"valid": bool, "email": str | None, "error": str | None}
    """
    if not license_key or not license_key.strip():
        return {"valid": False, "email": None, "error": "ライセンスキーを入力してください"}

    try:
        response = requests.post(
            GUMROAD_API_URL,
            data={
                "product_permalink": PRODUCT_PERMALINK,
                "license_key": license_key.strip(),
                "increment_uses_count": "false",  # カウントを増やさない
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
        return {"valid": False, "email": None, "error": f"認証エラー: {str(e)}"}
```

### Gumroad API の仕様

`POST https://api.gumroad.com/v2/licenses/verify` にフォームデータで送信します。

| パラメータ | 説明 |
|-----------|------|
| `product_permalink` | Gumroad商品のパーマリンク（URLの末尾） |
| `license_key` | ユーザーが入力したキー |
| `increment_uses_count` | `"false"` を推奨（真の検証時のみ `"true"`） |

レスポンスの `success: true` かつ `purchase.refunded: false` なら有効なライセンスです。

---

## 3. システムプロンプト設計

キャリア相談AIの品質を決めるのはシステムプロンプトです。

### core/prompts.py

```python
SYSTEM_PROMPT = """あなたは日本のITエンジニア専門のキャリアアドバイザーAIです。

## 専門領域
- エンジニアの転職・キャリアチェンジ
- スキルアップ・学習ロードマップの提示
- 年収・待遇交渉の戦略
- フリーランス転向の準備・リスク管理
- スタートアップ・大手・SIer各環境の比較

## 回答の原則
1. 具体的に: 抽象論より「次に何をすべきか」の行動レベルで回答
2. エンジニア視点で: 技術スタック・年収相場・市場動向に詳しい前提で話す
3. 共感を示す: 転職の不安は誰でも感じる、まず気持ちを受け止める
4. 限界を認める: キャリア相談の範囲外は専門家を紹介

## 禁止事項
- 特定の企業・エージェントの推薦（中立を保つ）
- 根拠のない給与保証
- 「必ずうまくいく」など過度な楽観発言
"""
```

### 設計上のポイント

**① 「禁止事項」を明示する**

「特定の企業を推薦しない」という制約を書くことで、AIが誤った方向に動くのを防ぎます。制約がないと、AIは時に「○○社が良さそうです」と根拠なく答えてしまいます。

**② 「回答の原則」で行動パターンを固定する**

「具体的に答えること」「エンジニア視点を持つこと」を明示することで、AIが一貫したキャラクターで動きます。

**③ プロンプトは短めに保つ**

長すぎるシステムプロンプトはキャッシュ効率が下がり、AIの応答品質にも影響します。CareerAIでは約600トークンに抑えました。

---

## 4. Streamlit アプリの実装

### app.py の核心部分

```python
import streamlit as st
from core.agent import chat, chat_premium
from core.license import verify_license

# セッション状態の初期化
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_premium" not in st.session_state:
    st.session_state.is_premium = False
if "message_count" not in st.session_state:
    st.session_state.message_count = 0

FREE_LIMIT = 10  # 無料版の上限

st.title("CareerAI - エンジニアのためのキャリア相談AI")

# ライセンスキー入力エリア
with st.sidebar:
    st.subheader("プレミアムプラン")
    license_key = st.text_input("ライセンスキー", type="password")
    
    if st.button("ライセンスを認証"):
        result = verify_license(license_key)
        if result["valid"]:
            st.session_state.is_premium = True
            st.success(f"認証成功！{result['email']} さん、プレミアムプランをご利用いただけます。")
        else:
            st.error(result["error"])

# 会話履歴の表示
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# メッセージ入力
if prompt := st.chat_input("キャリアについて相談してください..."):
    
    # 無料版の上限チェック
    if not st.session_state.is_premium and st.session_state.message_count >= FREE_LIMIT:
        st.warning(f"無料プランの上限（{FREE_LIMIT}回）に達しました。プレミアムプランへのアップグレードをご検討ください。")
        st.stop()
    
    # ユーザーメッセージを追加
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.write(prompt)
    
    # AI応答
    with st.chat_message("assistant"):
        with st.spinner("考え中..."):
            if st.session_state.is_premium:
                response = chat_premium(st.session_state.messages)
            else:
                response = chat(st.session_state.messages)
        
        st.write(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.message_count += 1
```

### Streamlitのセッション状態管理

Streamlitは各インタラクションでスクリプト全体が再実行されます。`st.session_state` を使って状態を保持することが必須です。

CareerAIで管理している状態:
- `messages`: 会話履歴（Claude APIに毎回送る）
- `is_premium`: ライセンス認証状態
- `message_count`: 無料版の使用回数

---

## 5. デプロイについて

### Streamlit Cloud（推奨）

公式の無料ホスティング。GitHubリポジトリと連携するだけでデプロイできます。

1. [share.streamlit.io](https://share.streamlit.io) にアクセス
2. GitHubリポジトリを連携
3. `app.py` のパスを指定
4. Secrets（`ANTHROPIC_API_KEY`）を設定

### requirements.txt

```
anthropic>=0.40.0
streamlit>=1.40.0
requests>=2.31.0
```

---

## 6. テスト戦略

```python
# tests/test_license.py
import pytest
from unittest.mock import patch, MagicMock
from core.license import verify_license


def test_verify_license_empty_key():
    """空のライセンスキーは False を返す"""
    result = verify_license("")
    assert result["valid"] is False
    assert result["error"] is not None


def test_verify_license_valid(mocker):
    """有効なキーは True と email を返す"""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "success": True,
        "purchase": {
            "email": "test@example.com",
            "refunded": False
        }
    }
    
    with patch("requests.post", return_value=mock_response):
        result = verify_license("valid-key-xxxx")
    
    assert result["valid"] is True
    assert result["email"] == "test@example.com"


def test_verify_license_timeout(mocker):
    """タイムアウト時はエラーメッセージを返す"""
    with patch("requests.post", side_effect=requests.Timeout):
        result = verify_license("some-key")
    
    assert result["valid"] is False
    assert "接続できません" in result["error"]
```

---

## まとめ

今回実装したCareerAIのポイントは3つです。

1. **プロンプトキャッシュ**で繰り返しのシステムプロンプト課金を削減
2. **Gumroadライセンス認証**でサーバーレスな有料プラン管理を実現
3. **Streamlit**でフロントエンド実装コストをほぼゼロに

個人開発でAIサービスを作る際の「コスト最適化 × 課金実装 × UI」の一つの答えを示せたと思います。

---

**実際に動くものを試してみたい方はこちら**

CareerAI（無料版: 月10回、有料版: ¥980買い切り）

https://aiagenta523-glitch.github.io/agenta_ventures/

GitHubリポジトリ: [aiagenta523-glitch/agenta_ventures](https://github.com/aiagenta523-glitch/agenta_ventures)
