# キャリア相談AI - エンジニアのためのAIメンター

日本のITエンジニア向けキャリア相談に特化したAIチャットアプリ。転職・スキルアップ・年収交渉・フリーランス転向など、エンジニアのキャリアの悩みに24時間即答する。

## 機能

- **キャリア相談チャット**: エンジニア特有の文脈でキャリアアドバイスを提供
- **マルチターン会話**: セッション内で会話の文脈を保持
- **無料/有料プラン分離**: 無料版（月10回/Claude Haiku）、有料版（無制限/Claude Sonnet）
- **Gumroadライセンス認証**: ライセンスキー入力でプレミアム解除
- **プロンプトキャッシュ**: `cache_control` でシステムプロンプトをキャッシュしコスト最適化

## ディレクトリ構成

```
career_ai/
├── app.py                  # Streamlit メインアプリ
├── core/
│   ├── agent.py            # Claude API 通信ロジック（プロンプトキャッシュ使用）
│   ├── prompts.py          # システムプロンプト定義
│   └── license.py          # Gumroad ライセンス検証
├── tests/
│   ├── test_agent.py
│   ├── test_license.py
│   └── test_prompts.py
├── .streamlit/
│   └── config.toml         # テーマ設定
├── requirements.txt
├── .env.example
└── README.md
```

## セットアップ手順

### 1. リポジトリをクローン / ダウンロード

```bash
git clone https://github.com/[your-org]/career-ai.git
cd career-ai
```

### 2. Python 仮想環境を作成・有効化

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数を設定

```bash
cp .env.example .env
# .env を編集して ANTHROPIC_API_KEY を設定する
```

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
```

Anthropic API キーは https://console.anthropic.com/ から取得する。

### 5. ローカルで起動

```bash
streamlit run app.py
```

ブラウザで http://localhost:8501 を開く。

### 6. テストを実行

```bash
pytest tests/ -v
```

---

## Streamlit Cloud へのデプロイ

### 手順

1. **GitHubにプッシュ**

   ```bash
   git add .
   git commit -m "Initial CareerAI MVP"
   git push origin main
   ```

2. **Streamlit Cloud でアプリを作成**

   - https://share.streamlit.io/ にアクセス
   - 「New app」をクリック
   - GitHubリポジトリを選択
   - Main file: `app.py` を指定
   - 「Deploy」をクリック

3. **Secrets に API キーを設定**

   Streamlit Cloud の「Settings」→「Secrets」に以下を追加:

   ```toml
   ANTHROPIC_API_KEY = "sk-ant-xxxxxxxxxxxx"
   ```

4. **デプロイ完了**

   `https://[your-app].streamlit.app` でアクセス可能になる。

---

## 有料版 (Gumroad) の設定

1. **Gumroad に商品を作成**

   | 項目 | 設定値 |
   |------|--------|
   | 商品名 | キャリア相談AI プレミアムプラン |
   | 価格 | ¥2,000/月（サブスクリプション） |
   | Permalink | `career-ai-monthly` |
   | ライセンスキー発行 | 有効にする |

2. **`core/license.py` の `PRODUCT_PERMALINK` を確認**

   ```python
   PRODUCT_PERMALINK = "career-ai-monthly"  # Gumroadの商品パーマリンクと一致させる
   ```

3. **`app.py` の購入リンクを更新**

   `https://gumroad.com/l/career-ai-monthly` を実際の Gumroad URL に変更する。

---

## コスト試算

| 項目 | 単価 | 月100ユーザー時 |
|------|------|-----------------|
| Claude Haiku（無料版） | ~$0.001/回 | $1 |
| Claude Sonnet（有料版） | ~$0.003/回 | $3 |
| Streamlit Cloud | 無料 | $0 |
| **合計** | | **~$4/月（約¥600）** |

プロンプトキャッシュにより、同一システムプロンプトの繰り返しコストを最大 90% 削減。

---

## 環境変数一覧

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `ANTHROPIC_API_KEY` | 必須 | Anthropic API キー |

---

## ライセンス

MIT License

---

*CareerAI - ventures/execution チーム制作 | 2026-04-19*
