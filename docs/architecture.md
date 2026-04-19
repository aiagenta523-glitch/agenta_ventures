# CareerAI システムアーキテクチャ

## 概要

CareerAIはStreamlitをフロントエンド、Anthropic Claude APIをバックエンドに使ったエンジニア向けキャリア相談Webアプリです。

```
┌─────────────────────────────────────────────────────┐
│                   ユーザーブラウザ                      │
│                   (Streamlit UI)                     │
└───────────────────────┬─────────────────────────────┘
                        │ HTTPS
┌───────────────────────▼─────────────────────────────┐
│              Streamlit Cloud (ホスティング)            │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │               app.py (メインUI)               │   │
│  │  - チャットUI・セッション管理                   │   │
│  │  - 使用回数制限 (無料: 10回/月)                │   │
│  │  - ライセンスキー認証フロー                    │   │
│  └────────────────┬────────────────────────────┘   │
│                   │                                 │
│  ┌────────────────▼────────────────────────────┐   │
│  │             core/ (ビジネスロジック)           │   │
│  │                                             │   │
│  │  agent.py          prompts.py               │   │
│  │  ├─ chat()         └─ SYSTEM_PROMPT         │   │
│  │  └─ chat_premium()    (エンジニア特化)        │   │
│  │                                             │   │
│  │  license.py                                 │   │
│  │  └─ verify_license()                        │   │
│  └────────────────┬──────────────┬─────────────┘   │
│                   │              │                  │
└───────────────────┼──────────────┼──────────────────┘
                    │              │
        ┌───────────▼───┐  ┌───────▼──────────┐
        │ Anthropic API │  │  Gumroad API     │
        │               │  │                  │
        │ Haiku (無料)  │  │ ライセンス検証   │
        │ Sonnet (有料) │  │ verify_license() │
        └───────────────┘  └──────────────────┘
```

## コンポーネント詳細

### app.py
- **役割**: StreamlitのエントリーポイントかつメインUI
- **主な機能**:
  - `st.session_state` でチャット履歴・使用カウント・プレミアム状態を管理
  - 無料版: `chat()` (Haiku, 最大1024トークン, 月10回)
  - 有料版: `chat_premium()` (Sonnet, 最大2048トークン, 無制限)
  - サイドバーにライセンスキー認証フォームを配置

### core/agent.py
- **役割**: Claude API通信コア
- **プロンプトキャッシュ**: システムプロンプトに `cache_control: {"type": "ephemeral"}` を設定し、繰り返しコストを最大90%削減
- **モデル分離**: 無料版 `claude-haiku-4-5`、有料版 `claude-sonnet-4-5`

### core/prompts.py
- **役割**: システムプロンプト定義
- **特徴**: エンジニア転職市場・スキルセット・年収レンジに特化した知識を注入

### core/license.py
- **役割**: Gumroadライセンスキー検証
- **フロー**: `POST https://api.gumroad.com/v2/licenses/verify` → 有効/無効をBoolで返す

## データフロー

### 無料ユーザーのチャットフロー
```
ユーザー入力
  → session_state.messages に追加
  → 使用回数チェック (>= 10で停止)
  → core/agent.chat(messages)
    → Anthropic API (Haiku)
    → キャッシュされたシステムプロンプト + 会話履歴
  → レスポンスをUIに表示
  → usage_count += 1
```

### ライセンス認証フロー
```
ライセンスキー入力
  → core/license.verify_license(key)
    → Gumroad API /v2/licenses/verify
    → product_permalink: "career-ai-monthly"
  → 有効: session_state.is_premium = True
  → 以降の会話でchat_premium()を使用
```

## 環境変数・シークレット

| 変数名 | 説明 | ローカル | Streamlit Cloud |
|--------|------|---------|----------------|
| `ANTHROPIC_API_KEY` | Anthropic API キー | `.env` | Secrets |
| `GUMROAD_ACCESS_TOKEN` | Gumroad API トークン | `.env` | Secrets |

## セキュリティ考慮事項

- APIキーはすべて環境変数経由（コードにハードコードしない）
- Gumroadライセンス検証はサーバーサイドのみ（フロントエンドで判断しない）
- セッション状態はユーザーブラウザのメモリに限定（永続化なし）

## スケーラビリティ

Streamlit Cloud の無料枠の制限:
- 1アプリ / 1GBメモリ / スリープあり（未アクセス時）
- 月間トラフィックが増えた場合は有料プラン（$25/月〜）へアップグレード
